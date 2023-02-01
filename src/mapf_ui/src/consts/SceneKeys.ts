enum SceneKeys
{
	Preloader = 'preloader',
	Controller = 'Controller',
}

enum SceneBusKeys
{
	BusDataChange = 'changedata',

	TopicTaskSet = 'topictaskset',			//Mapf Scene --> Tasks Scene
	TopicMAPFCall = 'topicmapfcall',		//Tasks Scene --> Mapf Scene()
	SetPhase = 'setphase',					//设置AGV作业阶段（目前两个阶段，一个是驻车点到起点，一个是起点到终点）

}

export {SceneKeys, SceneBusKeys}
