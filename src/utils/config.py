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
    cfg_ = None
    path2cfg_ = None

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
        if cls.path2cfg_:
            with open(cls.path2cfg_, 'w', encoding='utf-8') as fp:
                json.dump(cls.cfg_, fp, ensure_ascii=False)
            pass

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

        ret = [int(geometry['_x']), int(geometry['_y']),
               int(geometry['_x']) + int(geometry['_width']), int(geometry['_y']) + int(geometry['_height'])]
        return ret

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
                        'type': '',
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
                            'type': '',
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
        ret = params
        try:
            if 'rtsp_urls' in params.keys():  # 全局配置直接就替换了，但是需要更新view_ports的格式
                pass
            elif 'view_ports' in params.keys():
                # 根据params新设置过来的device_id和channel_id，更新cls.cfg_下面的各项值，或插入新项
                exist = False

                # 更新
                for it in cls.cfg_['rtsp_urls']:
                    if it['device_id'] == params['device_id'] and it['channel_id'] == params['channel_id']:  # update
                        it['rtsp_url'] = params['rtsp_url']
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
                cls.save_json()     # FIXME:有点野蛮，没有进行合法性校核，可能导致程序无法启动
                ret = cls.cfg_
            else:
                ret = None
        except KeyError as err:
            log.log(err, level=log.LOG_LVL_ERRO)
            ret = None
        finally:
            return ret
