import queue
import threading
import time

import cv2


class VideoCaptureThread(threading.Thread):
    def __init__(self, url, result_queue):
        super().__init__()
        self.daemon = True
        # rtsp地址
        self.__rtsp_url = url
        # 存放帧的队列
        self.__queue = result_queue
        # 标记是否退出线程
        self.__is_exit = False
        # 是否取帧
        self.__is_grab_frame = False
        # 流信息
        self.__width = 0
        self.__height = 0
        self.__fps = 0
        self.__current_frame_pos = 0

    def close(self):
        """
        退出线程
        :return: 无
        """
        self.__is_exit = True

    def grab_frame(self):
        """
        标记是否取一帧图像
        :return: 无
        """
        self.__is_grab_frame = True

    def get_stream_info(self) -> ():
        """
        返回流信息
        :return: 元组，(w, h, fps)
        """
        return self.__width, self.__height, self.__fps

    def get_stream_frame_pos(self) -> int:
        """
        返回帧位置
        :return: int
        """
        return self.__current_frame_pos

    def run(self):
        try:
            cap_obj = cv2.VideoCapture(self.__rtsp_url)
        except cv2.error as err:
            print(f"cv2.VideoCapture failed: {err}")
            return

        if not cap_obj.isOpened():
            return

        if self.__is_exit is True:
            # 在阻塞连接流这段时间，上层已经等不及而关闭该线程
            if cap_obj is not None:
                # print('Force kill capture obj.')
                cap_obj.release()
                return

        self.__queue.put("success")
        # 读取流信息
        self.__fps = int(cap_obj.get(cv2.CAP_PROP_FPS))
        self.__width = int(cap_obj.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.__height = int(cap_obj.get(cv2.CAP_PROP_FRAME_HEIGHT))
        # 设置缓存
        cap_obj.set(cv2.CAP_PROP_BUFFERSIZE, 0)
        # 循环读
        while self.__is_exit is False:
            self.__current_frame_pos = cap_obj.get(cv2.CAP_PROP_POS_FRAMES)
            # 是否要取最新一帧
            if self.__is_grab_frame is True:
                (success, img) = cap_obj.read()
                if success is True:
                    self.__is_grab_frame = False
                    self.__queue.queue.clear()
                    self.__queue.put_nowait(img)
                else:
                    # 退出线程主循环
                    self.close()
            else:
                # 丢弃帧
                cap_obj.grab()
            # 每秒25帧：1000 / 25 = 40ms，理解间隔为40ms，实际设置为10ms
            time.sleep(0.01)
        cap_obj.release()


class GrabFrame:
    # 打开流最多等待多少时间
    OPEN_RTSP_TIMEOFF = 10

    def __init__(self):
        # 存放帧数据
        self.__queue = queue.Queue(2)
        # 取帧线程
        self.__capture_thread = None
        # 缓存当前的url和延时设置
        self.rtsp_url_ = None
        self.timeout_ = None

    def open_stream(self, url, timeout) -> bool:
        """
        打开指定url地址的流，并根据timeout参数进行超时
        :param url: 流地址
        :param timeout: 打开流的超时时间，单位：s，0：阻塞
        :return: 打开流是否成功
        """
        # 合法性检测
        if url is None or len(url) <= 7 or timeout < 0:
            return False

        # 存放返回值
        self.__capture_thread = VideoCaptureThread(url, self.__queue)
        self.__capture_thread.setName('VideoCaptureThread')
        # 启动读取流线程
        self.__capture_thread.start()
        ret = False
        # 超时等待
        try:
            _ = self.__queue.get(block=True, timeout=timeout if timeout > 0 else None)
        except queue.Empty:
            # print(f'cv2.VideoCapture: could not open stream ({url}). Timeout after {timeout}s')
            self.__capture_thread.close()
            ret = False
        else:
            # print(f'cv2.VideoCapture: open stream ({url}) successes. ')
            # 缓存timeout和url，如果需要重连，则使用它们。
            self.timeout_ = timeout
            self.rtsp_url_ = url
            ret = True
        finally:
            # 释放资源
            self.__queue.queue.clear()
            return ret

    def read_frame(self, timeout=5) -> None or any:
        """
        读取当前流最新的一帧图像数据
        :param timeout: 取帧的超时时间，单位：s，0：阻塞
        :return: 帧数据
        """
        _frame = None
        if self.__capture_thread is None or timeout < 0:
            return _frame

        # TODO: 如果多线程调用该函数read_frame，此处需要加锁Lock()
        self.__capture_thread.grab_frame()
        try:
            _frame = self.__queue.get(block=True, timeout=timeout if timeout > 0 else None)
        except queue.Empty:
            # print(f'cv2.read: could not read frame. Timeout after {timeout}s,{self.__capture_thread}')
            # 如果线程已经退出，就应该重新起线程。
            if not self.__capture_thread.isAlive():
                self.__capture_thread = None
                if self.rtsp_url_ and self.timeout_:
                    self.open_stream(self.rtsp_url_, self.timeout_)
        else:
            self.__queue.queue.clear()
        return _frame

    def get_stream_info(self) -> ():
        """
        获取流信息
        :return: 返回元组(流宽度， 流高度， 帧率)
        """
        if self.__capture_thread is not None:
            return self.__capture_thread.get_stream_info()
        else:
            return 0, 0, 0

    def get_stream_frame_pos(self) -> int:
        """
        返回帧位置
        :return: int
        """
        if self.__capture_thread.isAlive():
            return self.__capture_thread.get_stream_frame_pos()
        else:
            return -1

    def stop_stream(self):
        """
        关闭流
        """
        # 清空队列
        self.__queue.queue.clear()
        self.__queue = None

        # 退出读取线程
        if self.__capture_thread is not None:
            self.__capture_thread.close()
            self.__capture_thread.join()
            self.__capture_thread = None
