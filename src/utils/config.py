#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2021 The CASICloud Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
# pylint: disable=invalid-name
# pylint: disable=missing-docstring

"""
=========================
config module
=========================

Configuration related stuff here.
1个视频通道对应rtsp的url
1个视频通道包含多个预置点viewpoint
1个预置点包含多个热点区aoi
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0

import json
from utils import log


class ConfigSet:
    baseconfig_ = None      # 本地配置
    path2basecfg_ = None    # 本地配置路径
    cfg_ = None             # 下发配置
    path2cfg_ = None        # 下发配置路径

    @classmethod
    def load_json(cls, fp):
        try:
            load_dict = None
            cls.path2cfg_ = fp
            with open(fp, 'r', encoding='UTF-8') as load_f:
                load_dict = json.load(load_f)
                load_f.close()
        finally:
            return load_dict

    @classmethod
    def save_json(cls):
        formatted_cfg = json.dumps(cls.cfg_, ensure_ascii=False, indent=2)
        if cls.path2cfg_:
            with open(cls.path2cfg_, 'w', encoding='utf-8') as fp:
                fp.write(formatted_cfg)
                fp.close()

    @classmethod
    def get_basecfg(cls, pathtobasecfg='baseconfig.cfg'):
        load_dict = None
        try:
            if cls.baseconfig_ is None:
                with open(pathtobasecfg, 'r', encoding='UTF-8') as load_f:
                    load_dict = json.load(load_f)
                cls.baseconfig_ = load_dict
                cls.path2basecfg_ = pathtobasecfg
            else:
                load_dict = cls.baseconfig_
        finally:
            return load_dict

    @classmethod
    def save_basecfg(cls):
        ret = False
        try:
            formatted_cfg = json.dumps(cls.baseconfig_, ensure_ascii=False, indent=2)
            if cls.path2basecfg_:
                with open(cls.path2basecfg_, 'w', encoding='utf-8') as fp:
                    fp.write(formatted_cfg)
            ret = True
        finally:
            return ret

    @classmethod
    def get_cfg(cls, pathtocfg='v2v.cfg'):
        if cls.cfg_ is None:
            cls.cfg_ = cls.load_json(pathtocfg)
        return cls.cfg_

    @classmethod
    def geometry_fix(cls, mxcell):
        geometry = mxcell['mxCell']['mxGeometry']
        if '_x' not in geometry.keys():
            geometry['_x'] = 0
        if '_y' not in geometry.keys():
            geometry['_y'] = 0
        if '_width' not in geometry.keys():
            geometry['_width'] = 0
        if '_height' not in geometry.keys():
            geometry['_height'] = 0

        ret = [
            int(float(geometry['_x'])),
            int(float(geometry['_y'])),
            int(float(geometry['_x']) + float(geometry['_width'])),
            int(float(geometry['_y']) + float(geometry['_height']))
        ]

        # 如果是特殊的液位计，需要多边形内部的座标
        try:
            style = mxcell['mxCell']['_style']
            # style: 'polygon;polyCoords=[[10,10],[50,10],[84.76307531380758,107.06191742071053],[10,90]];'
            coords = style[style.find('polyCoords'):].split(';')[0][len('polyCoords') + 1:]
            jso = json.loads(coords)
            # jso is a list: [[10, 10], [50, 10], [84.76307531380758, 107.06191742071053], [10, 90]]
            coordslist = []
            for pt in jso:
                coordslist.append(int(pt[0]) + ret[0])
                coordslist.append(int(pt[1]) + ret[1])
            ret = coordslist
        except KeyError as err:
            log.log(f'[{__file__}]{err}', level=log.LOG_LVL_WARN)
        except json.decoder.JSONDecodeError as err:
            log.log(f'[{__file__}]{err}', level=log.LOG_LVL_WARN)
        return ret

    @classmethod
    def validate_cfg(cls, config):
        """
        在全通道配置下发保存到配置文件之前，最后校验一次合法性，并合并优化调用方式（同一个ai service，不要多次调用）。
        这个函数后续需要和整个配置模块一起优化重构。
        :param config:
        :return:
        """
        channels = config['rtsp_urls']

        for ch in channels:
            for vp in ch['view_ports']:
                ai_set = set()  # 在某个预置点，收集该预置点下配置的所有ai地址，以合并重复项
                presetid = list(vp.keys())[0]
                aois = vp[presetid]
                for aoi in aois:
                    ai_set.add(aoi['ai_service'])

                merged_aois = []
                for ai in ai_set:
                    new_aoi = {
                        'ai_service': ai,
                        'area_of_interest': []
                    }

                    for oldaoi in aois:
                        if oldaoi['ai_service'] == ai:
                            new_aoi['area_of_interest'] = new_aoi['area_of_interest'] + oldaoi['area_of_interest']
                            new_aoi['seconds'] = oldaoi['seconds']
                    merged_aois.append(new_aoi)

                vp[presetid] = merged_aois
            pass
        return config

    @classmethod
    def ui2ai(cls, vps):
        """
        输入ui配置层发来的dict:{'preset1':{...}, 'preset2': {...}, ...}
        返回list:[{'preset1': [...]}, {'preset2': [...]}, ...]
        因为ui的一个preset，比如preset4包含了多个不同的ai_service，比如plc、person、panel，
        所以preset4会按ai_service进一步细分为进一步细分，返回的最终形式如下。
        [
            {'preset1': [...]},
            {'preset2': [...]},
            ...,
            {'preset4':
                [{'seconds': 5,
                  'ai_service': 'xxx',
                  'area_of_interest':
                    [{"name": "PLC_01", "type": "", "score": 0, "pos": [594, 516, 620, 542], "value": ""},
                     {...}, ... ]},
                 {'seconds': 5,
                  'ai_service': 'yyy',
                  'area_of_interest':
                    [{"name": "OCR_01", "type": "", "score": 0, "pos": [594, 516, 620, 542], "value": ""},
                     {...}, ... ]},
                ]
             },
             ...
        ]
        目前支持的模型类型包括：
        '人数':'person',
        '频率':'PLC',
        ----------------
        '字符':'OCR',
        '液位':'LLM'
        '指针':'METER',
        '开关':'SWITCH',
        '指示灯':'IDL',
        """

        listvps = []
        li = {}
        for key in vps.keys():
            vp = vps[key]  # vp是preset1这样一个view_port预置点

            aois = vp['mxGraphModel']['root']
            # ['Rect', 'Roundrect', 'Shape', 'Text'] for example
            ai_list = [aoi for aoi in aois.keys() if aoi not in ['Diagram', 'Layer']]
            lis = []    # containe divided preset4, preset4, ...
            for jk in ai_list:
                if 'seconds' not in vp.keys():
                    vp['seconds'] = 5
                li[key] = {
                    'seconds': vp['seconds'],  # vp from ui include 'seconds', 'mxGraphModel' keys.
                }
                categories_aois = aois[jk]  # 第三重循环！aois分为Rect、Text等多类，需逐项改，categories_aois对应如：Rect。
                aoi_list = []  # 这个最终容器放ai需要的区域矩形列表。
                li[key]['area_of_interest'] = aoi_list
                # Oh,no, the format is different!
                if type(categories_aois) is dict:
                    mxcell = categories_aois
                    li[key]['ai_service'] = mxcell['_href']  # 每个ai模型类别的ai_service微服务链接都一样，随便取一个
                    aoi_item = {
                        'name': mxcell['_label'],
                        'type': jk,
                        'score': None,
                        'pos': cls.geometry_fix(mxcell),
                        'value': None
                    }
                    aoi_list.append(aoi_item)
                elif type(categories_aois) is list:
                    for mxcell in categories_aois:
                        li[key]['ai_service'] = mxcell['_href']  # 每个ai模型类别的ai_service微服务链接都一样，随便取一个
                        aoi_item = {
                            'name': mxcell['_label'],
                            'type': jk,
                            'score': None,
                            'pos': cls.geometry_fix(mxcell),
                            'value': None
                        }
                        aoi_list.append(aoi_item)
                lis.append(li[key])
            listvps.append({key: lis})
        return listvps

    @classmethod
    def update_cfg(cls, params):
        """
        功能1：将UI模块的配置信息格式化为v2v的标准配置格式（以AI需求为主）
        功能2：将cls.cfg_内容更新
        功能3：更新的配置保存到本地的配置文件
        功能4：返回配置信息
        Parameters
        ----------
        params:  Dict类型，可能是某单路视频通道配置，可能是全局配置。

        Returns
        -------
        Dict
            通用格式。
        Raises
        ----------
        RuntimeError
            待定.
        """
        ret = None
        try:
            # 全局配置直接就替换了，但是因为所有的配置项都是字符类型，需要先json对象化
            if 'rtsp_urls' in params.keys():
                # rtsp_urls，mqtt_svrs，micro_service是对象，需要重建
                o_rtsp_urls = json.loads(params['rtsp_urls'])
                k_rtsp_urls = []
                for rtspobj in o_rtsp_urls:
                    obj = {
                        'device_id': rtspobj['device_id'],
                        'channel_id': rtspobj['channel_id'],
                        'rtsp_url': rtspobj['rtsp_url'],
                        'name': rtspobj['name'],
                        'sample_rate': rtspobj['sample_rate'],
                        'view_ports': cls.ui2ai(rtspobj['view_ports'])
                    }
                    k_rtsp_urls.append(obj)
                o_mqtt_svrs = json.loads(params['mqtt_svrs'])
                o_micro_service = json.loads(params['micro_service'])
                cfgobj = {'version': params['version'],
                          'rtsp_urls': k_rtsp_urls,
                          'mqtt_svrs': o_mqtt_svrs,
                          'micro_service': o_micro_service,
                          'nvr_samples': params['nvr_samples'],
                          'ui_config_dir': params['ui_config_dir'],
                          'media_service': params['media_service'],
                          'ipc_ptz_delay': params['ipc_ptz_delay']}
                cls.cfg_ = cfgobj
            elif 'view_ports' in params.keys():
                # 根据params新设置过来的device_id和channel_id，更新cls.cfg_下面的各项值，或插入新项
                exist = False

                # 更新
                for it in cls.cfg_['rtsp_urls']:
                    if it['device_id'] == params['device_id'] and it['channel_id'] == params['channel_id']:  # update
                        # 在目前的ui测试界面，没有设置rtsp_url和name，默认为''
                        if params['rtsp_url'] != '':
                            it['rtsp_url'] = params['rtsp_url']
                        if params['name'] != '':
                            it['name'] = params['name']
                        it['sample_rate'] = params['sample_rate']
                        it['view_ports'] = cls.ui2ai(json.loads(params['view_ports']))
                        exist = True
                # 或者插入
                if not exist:
                    obj = {
                        'device_id': params['device_id'],
                        'channel_id': params['channel_id'],
                        'rtsp_url': params['rtsp_url'],
                        'name': params['name'],
                        'sample_rate': params['sample_rate'],
                        'view_ports': cls.ui2ai(json.loads(params['view_ports']))
                    }
                    cls.cfg_['rtsp_urls'].append(obj)
            # 保存配置文件
            cls.cfg_ = cls.validate_cfg(cls.cfg_)
            cls.save_json()     # FIXME:有点野蛮，没有进行合法性校核，可能导致程序无法启动
            ret = cls.cfg_
        except KeyError as err:
            log.log(f'[{__file__}]{err}', level=log.LOG_LVL_ERRO)
            ret = None
        finally:
            return ret
