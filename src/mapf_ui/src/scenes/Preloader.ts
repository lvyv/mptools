import Phaser from 'phaser'

import TextureKeys from '../consts/TextureKeys'
import {SceneKeys} from '../consts/SceneKeys'

export default class Preloader extends Phaser.Scene
{
	constructor()
	{
		super(SceneKeys.Preloader)
	}

	preload()
	{
		this.load.image(TextureKeys.Universe, 'universe/bg.jpg')
        this.load.atlas(TextureKeys.Atlas,"./assets/atlas/agv.png" , "./assets/atlas/agv.json");
		this.load.atlas(TextureKeys.Ui, 'universe/ui.png', 'universe/ui.json')
        this.load.bitmapFont(TextureKeys.Digital, 'universe/digital.png', 'universe/digital.xml')
		this.load.image(TextureKeys.Logo, 'universe/white.logo.png')
		this.load.image(TextureKeys.StarsWindow, 'assets/stars-window.png')
		this.load.image(TextureKeys.Star, 'assets/star2.png')
		this.load.image(TextureKeys.StoreDetailWindow, 'assets/store-detail-window.png')
		this.load.image(TextureKeys.RightTopWindow, 'assets/right-top-window.png')
		this.load.image(TextureKeys.RightMiddleWindow, 'assets/right-middle-window.png')
		this.load.image(TextureKeys.ZxkWindow, 'assets/zxk-window.png')
	    this.load.tilemapTiledJSON(TextureKeys.ZxkMap, './assets/tilemaps/zxk.json')
        this.load.image(TextureKeys.PathTileSet,'./assets/tilesets/path-tile-set.png')
        this.load.image(TextureKeys.Cad, './assets/cad.png')
	}

	create()
	{
		this.scene.start(SceneKeys.Controller)
	}
}
