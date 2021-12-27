//定义常量
const  API_SETUP_SINGLE_CHANNEL = "/api/v1/v2v/setup_single_channel";
const  API_GET_PRESETS_PIC_PREFIX = '/api/v1/v2v/presets/'
const V2V_CONFIG_CACHE = "local_v2v_configuration_";
const EMPTY_GRAPH_MODEL = '<mxGraphModel><root>\
                           <Diagram label="照片标注" href="https://github.com/lvyv/mptools" id="0"><mxCell /></Diagram>\
                           <Layer label="Default Layer" id="1"><mxCell parent="0" /></Layer>\
                          </root></mxGraphModel>';
const local_v2v_conf_aoi = {"root": {
            "Diagram": {"mxCell": "", "_label": "照片标注", "_href": "https://github.com/lvyv/mptools", "_id": "0"},
            "Layer": {"mxCell": {"_parent": "0"}, "_label": "Default Layer", "_id": "1"}}};

//全局变量
let v2v_app_ = {"editor": {}};
let local_v2v_configuration_ = null;

//基本函数
function getContainer() {
    return document.querySelector("#viewports");
}

function getMatches(container) {
    return container.querySelectorAll(".preview_img");
}

function getPresetSelector(presetId) {
    return document.querySelector(`#preset${presetId}`);
}

function onLoadingLogo() {
    document.body.classList.add("loading");
}

function unLoadingLogo() {
    document.body.classList.remove("loading");
}

function loadV2VConfCache() {
    return window.localStorage.getItem(V2V_CONFIG_CACHE);
}

function saveV2VConfCache(v2vConf) {
    window.localStorage.setItem(V2V_CONFIG_CACHE, v2vConf);
}

// 设置缩略图
function setThumbnailToSelector(nodeSelector, data , width, height) {
    let base64 = 'data:image/png;base64, ' + data;
    nodeSelector.setAttribute('src', base64);
    nodeSelector.setAttribute('ori_width', width);
    nodeSelector.setAttribute('ori_height', height);
    nodeSelector.setAttribute('ori_image', true);    //说明存在png大图
}

function setPresetId(id){

    if(local_v2v_configuration_.defaultPresetId == undefined || local_v2v_configuration_.defaultPresetId == null)
    {
        local_v2v_configuration_.defaultPresetId = id;
    }else
    {
        local_v2v_configuration_.defaultPresetId = Math.min(local_v2v_configuration_.defaultPresetId, id);
    }
}

function setThumbnail(data) {
    for (let idx in data.presets) {
        let  url = data.presets[idx];
        let items = url.split('/');
        setThumbnailToSelector(getPresetSelector(items[items.length - 1]),
            mxUtils.load(url).getText(), data.width, data.height);
        setPresetId(items[items.length - 1]);
    }
}

//全局变量初始化
function load_local_v2v_configuration() {
    let cache = loadV2VConfCache();
    if (cache) {
        local_v2v_configuration_ = JSON.parse(cache);
        local_v2v_configuration_.current_preset = null ; // 初始化为正确状态很重要
        return;
    }
    local_v2v_configuration_ = {
        device_id: '',  // v2v后端提供，CDM设置
        channel_id: '',  // v2v后端提供，CDM设置
        rtsp_url: '',  // v2v后端提供，CDM设置
        name: '',                    // v2v后端提供，CDM设置
        sample_rate: 1,                     // 用户设置，CDM中选择
        presets: {},                        // 用户设置，所有的view_port标注
        current_preset: null,               // 程序内部使用
        defaultPresetId : null
    };
    // 读取html节点，看有多少个view_port，预置点
    let matches = getMatches(getContainer());
    for (let iii = 0; iii < matches.length; iii++) {
        local_v2v_configuration_.presets[matches[iii].id] = {
            seconds: 5,                       // seconds - 要停止在当前预置点多少时间
            mxGraphModel: local_v2v_conf_aoi  // mxGrapModel - aoi，兴趣点 FIXME
        };
    }
}

//editor模型 ==> json模型
function get_json_model(editor) {
    let xmlNode = new mxCodec().encode(editor.graph.getModel());
    return new X2JS().xml2json(xmlNode);
}

//editor模型 <== json模型
function set_json_model(editor, jso) {
    if (jso.mxGraphModel) {
        let xmlO = new X2JS().json2xml({mxGraphModel: jso.mxGraphModel});
        new mxCodec(xmlO).decode(xmlO.documentElement, editor.graph.getModel());
    } else {
        let doc = mxUtils.parseXml(EMPTY_GRAPH_MODEL);
        new mxCodec(doc).decode(doc.documentElement, editor.graph.getModel());
    }
}

// Program starts here. The document.onLoad executes the
// createEditor function with a given configuration.
// In the config file, the mxEditor.onInit method is
// overridden to invoke this global function as the
// last step in the editor constructor.
function onInit(editor) {
    // Enables rotation handle
    mxVertexHandler.prototype.rotationEnabled = true;

    // Enables guides
    mxGraphHandler.prototype.guidesEnabled = true;

    // Alt disables guides
    mxGuide.prototype.isEnabledForEvent = function (evt) {
        return !mxEvent.isAltDown(evt);
    };

    // Enables snapping waypoints to terminals
    mxEdgeHandler.prototype.snapToTerminals = true;

    // Defines an icon for creating new connections in the connection handler.
    // This will automatically disable the highlighting of the source vertex.
    mxConnectionHandler.prototype.connectImage = new mxImage('images/connector.gif', 16, 16);

    // Enables connections in the graph and disables
    // reset of zoom and translate on root change
    // (ie. switch between XML and graphical mode).
    editor.graph.setConnectable(false);

    // Clones the source if new connection has no target
    editor.graph.connectionHandler.setCreateTarget(true);

    editor.graph.setGridSize(1);

    // Handles keystroke events
    var keyHandler = new mxKeyHandler(editor.graph);

    // Handles cursor keys
    var nudge = function (keyCode) {
        if (!editor.graph.isSelectionEmpty()) {
            var dx = 0;
            var dy = 0;

            if (keyCode == 37) {
                dx = -1;
            } else if (keyCode == 38) {
                dy = -1;
            } else if (keyCode == 39) {
                dx = 1;
            } else if (keyCode == 40) {
                dy = 1;
            }

            editor.graph.moveCells(editor.graph.getSelectionCells(), dx, dy);
        }
    };

    // Ignores enter keystroke. Remove this line if you want the
    // enter keystroke to stop editing
    keyHandler.enter = function () {
    };

    keyHandler.bindKey(37, function () {
        nudge(37);
    });

    keyHandler.bindKey(38, function () {
        nudge(38);
    });

    keyHandler.bindKey(39, function () {
        nudge(39);
    });

    keyHandler.bindKey(40, function () {
        nudge(40);
    });

    // 定义预置点的预览图片被点击的事件处理函数
    let loadImageCallback = function (editor, nd) {
        // 一旦选中某个预置点，正确处理逻辑是保存现有的
        let curid = local_v2v_configuration_.current_preset;
        if (!curid) {
            curid = nd.id; // 启动以来从来没有点击选择过
            let md = local_v2v_configuration_.presets[nd.id];
            set_json_model(editor, md)
        }
        local_v2v_configuration_.presets[curid].mxGraphModel = get_json_model(editor);
        local_v2v_configuration_.current_preset = nd.id;
        let md = local_v2v_configuration_.presets[nd.id];
        set_json_model(editor, md);
        if (nd.getAttribute('ori_image')) {
            let url = `/viewport/${local_v2v_configuration_.device_id}/${nd.id.substring(6)}.png`
            //editor.graph.setBackgroundImage(new mxImage(url, nd.getAttribute('ori_width'), nd.getAttribute('ori_height')));
            editor.graph.setBackgroundImage(new mxImage(url, 680, 480));
        } else {
            editor.graph.setBackgroundImage(new mxImage('/viewport/add-viewport.png', 680, 480));
        }
        editor.execute('fit');
        editor.graph.view.validate();	//必须调用以刷新视图背景
    };
    editor.addAction('loadImage', loadImageCallback);

    /***** 定义预置点操作 *****/
    let matches = getMatches(getContainer())
    for (let iii = 0; iii < matches.length; iii++) {
        mxEvent.addListener(matches[iii], 'click', function (evt) {
            editor.execute('loadImage', evt.currentTarget);
        });
    }
    // Defines a new action to switch between
    // XML and graphical display
    let textNode = document.getElementById('xml');
    let graphNode = editor.graph.container;
    let sourceInput = document.getElementById('source');
    sourceInput.checked = false;

    let switchViewCallback = function (editor) {
        if (sourceInput.checked) {
            graphNode.style.display = 'none';
            textNode.style.display = 'inline';
            let node = new mxCodec().encode(editor.graph.getModel());
            textNode.value = mxUtils.getPrettyXml(node);
            textNode.originalValue = textNode.value;
            textNode.focus();
        } else {
            graphNode.style.display = '';
            if (textNode.value != textNode.originalValue) {
                let doc = mxUtils.parseXml(textNode.value);
                new mxCodec(doc).decode(doc.documentElement, editor.graph.getModel());
            }
            textNode.originalValue = null;
            // Makes sure nothing is selected in IE
            if (mxClient.IS_IE) {
                mxUtils.clearSelection();
            }
            textNode.style.display = 'none';
            // Moves the focus back to the graph
            editor.graph.container.focus();
        }
    };

    editor.addAction('switchView', switchViewCallback);

    // Defines a new action to switch between
    // XML and graphical display
    mxEvent.addListener(sourceInput, 'click', function () {
        editor.execute('switchView');
    });

    $('#group_labels').click(function () {
        editor.execute('group');
    });
    $('#ungroup_labels').click(function () {
        editor.execute('ungroup');
    });
    $('#select_all').click(function () {
        editor.execute('selectAll');
    });
    $('#deselect_all').click(function () {
        editor.execute('selectNone');
    });
    $('#zoom_in').click(function () {
        editor.execute('zoomIn');
    });
    $('#zoom_out').click(function () {
        editor.execute('zoomOut');
    });
    $('#original_size').click(function () {
        editor.execute('actualSize');
    });
    $('#fit_window').click(function () {
        editor.execute('fit');
    });
    $('#set_cfg').click(function () {
        //保存当前预制位模型
        if (local_v2v_configuration_.current_preset) {
            local_v2v_configuration_.presets[local_v2v_configuration_.current_preset].mxGraphModel = get_json_model(editor);
        }
        let report_presets = {};
        // 将标记过的预置位图片上报
        let filtered = Object.keys(local_v2v_configuration_.presets).filter(function (value) {
            let keyset = Object.keys(local_v2v_configuration_.presets[value].mxGraphModel.root) //FIXME
            let labeled = keyset.filter(value => {
                return (value !== 'Diagram' & value !== 'Layer')
            })
            return labeled.length > 0;
        })
        filtered.forEach(function (key) {
            report_presets[key] = local_v2v_configuration_.presets[key];
        })
        console.log(report_presets);
        postSetupSingleChannel(report_presets);
    });

    /* 自定义初始化操作 */
    load_local_v2v_configuration();
    //add 测试数据
    local_v2v_configuration_.device_id = '34020000001320000001';
    local_v2v_configuration_.channel_id = '34020000001310000001';

    //预览初始化
    init_preview(local_v2v_configuration_.device_id, local_v2v_configuration_.channel_id, true);


    // 本函数实现页面初始化的时候，更新预置点的thumbnail栏。
    function init_preview(devid, channelid, refresh) {
        let onload = function (req) {
            if (req.getStatus() == 200) {
                let data = JSON.parse(req.getText());
                local_v2v_configuration_.rtsp_url = data.rtsp_url
                setThumbnail(data);
                loadImageCallback(editor, getPresetSelector(local_v2v_configuration_.defaultPresetId))
            }
            unLoadingLogo();
        }
        let onerror = function () {
            mxUtils.alert('Error');
            unLoadingLogo();
        }
        let url = API_GET_PRESETS_PIC_PREFIX +`${devid}/${channelid}?refresh=${refresh}`;
        onLoadingLogo();
        mxUtils.get(url, onload, onerror);
    };

}

//离开当前页面(刷新或关闭)时执行
window.onbeforeunload = function () {
    if (local_v2v_configuration_.current_preset) {
        local_v2v_configuration_.presets[local_v2v_configuration_.current_preset].mxGraphModel = get_json_model(v2v_app_.editor);
    }
    saveV2VConfCache(JSON.stringify(local_v2v_configuration_));
    console.log(local_v2v_configuration_);
};

//ajax post 相关请求
function  postJsonData(url , data) {
    $.ajax({
        type: "post",
        url: url,
        async: true,
        headers: {"Content-Type": "application/json", "accept": "application/json", "name": "666"},
        dataType: "json",
        data: JSON.stringify(data),
        success: function (res) {
            console.log('OK');
            console.log(res);
        },
        error: function () {
            console.log("fail");
        }
    })
}

function  postSetupSingleChannel(presetData) {
   let data = {
        "rtsp_url": local_v2v_configuration_.rtsp_url,
        "device_id": local_v2v_configuration_.device_id,
        "channel_id": local_v2v_configuration_.channel_id,
        "name": local_v2v_configuration_.name,
        "sample_rate": local_v2v_configuration_.sample_rate,
        "view_ports": JSON.stringify(presetData)
    }
    postJsonData(API_SETUP_SINGLE_CHANNEL, data)
}