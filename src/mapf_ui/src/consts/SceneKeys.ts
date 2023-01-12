enum SceneKeys
{
	Preloader = 'preloader',
	Controller = 'Controller',
	Game = 'game',
	GameOver = 'game-over'
}

enum SceneBusKeys
{
	BusDataChange = 'changedata',

	TopicTaskSet = 'topictaskset',		//Mapf Scene --> Tasks Scene
	TopicMAPFCall = 'topicmapfcall'		//Tasks Scene --> Mapf Scene()

}

export {SceneKeys, SceneBusKeys}
