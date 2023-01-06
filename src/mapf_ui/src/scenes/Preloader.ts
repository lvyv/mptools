import Phaser from 'phaser'

import TextureKeys from '../consts/TextureKeys'
import SceneKeys from '../consts/SceneKeys'
import AnimationKeys from '../consts/AnimationKeys'

export default class Preloader extends Phaser.Scene
{
	constructor()
	{
		super(SceneKeys.Preloader)
	}

	preload()
	{
		this.load.image(TextureKeys.Background, 'house/bg_repeat_340x640.png')
		this.load.image(TextureKeys.MouseHole, 'house/object_mousehole.png')
		this.load.image(TextureKeys.Window1, 'house/object_window1.png')
		this.load.image(TextureKeys.Window2, 'house/object_window2.png')
		this.load.image(TextureKeys.Bookcase1, 'house/object_bookcase1.png')
		this.load.image(TextureKeys.Bookcase2, 'house/object_bookcase2.png')
		this.load.image(TextureKeys.LaserEnd, 'house/object_laser_end.png')
		this.load.image(TextureKeys.LaserMiddle, 'house/object_laser.png')
		this.load.image(TextureKeys.Coin, 'house/object_coin.png')
		this.load.atlas(TextureKeys.RocketMouse, 'characters/mouse.png', 'characters/mouse.json')

		this.load.image(TextureKeys.Universe, 'universe/bg.jpg')
        this.load.atlas(TextureKeys.Space, 'universe/space.png', 'universe/space.json')
        this.load.atlas(TextureKeys.Ui, 'universe/ui.png', 'universe/ui.json')
        this.load.bitmapFont(TextureKeys.Digital, 'universe/digital.png', 'universe/digital.xml')

		this.load.image(TextureKeys.Logo, 'universe/white.logo.png')

		this.load.image(TextureKeys.StarsWindow, 'assets/stars-window.png')
		this.load.image(TextureKeys.Star, 'assets/star2.png')

		this.load.image(TextureKeys.ZxkWindow, 'assets/zxk-window.png')
		this.load.image(TextureKeys.GreenPanel, 'assets/green-panel.png')

	}

	create()
	{
		// this.scene.start(SceneKeys.Game)
		this.scene.start(SceneKeys.Controller)
	}
}
