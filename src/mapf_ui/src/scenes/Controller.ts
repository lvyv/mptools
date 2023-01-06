import TextureKeys from '~/consts/TextureKeys'
import {UiLabels, UiLayout} from '../consts/UiLabels'
import Stars from './Stars'
import Mapf from './Mapf'

export default class Controller extends Phaser.Scene {

    // private background!: Phaser.GameObjects.TileSprite
    private panel_container!: Phaser.GameObjects.Container
	private button1!: Phaser.GameObjects.Image
	private button2!: Phaser.GameObjects.Image
	private button3!: Phaser.GameObjects.Image
	private button4!: Phaser.GameObjects.Image
	private button5!: Phaser.GameObjects.Image
	private button6!: Phaser.GameObjects.Image
    private text1!: Phaser.GameObjects.BitmapText
    private text2!: Phaser.GameObjects.BitmapText
	private toggle1!: Phaser.GameObjects.Image
	private toggle2!: Phaser.GameObjects.Image
    private padUp!: Phaser.Geom.Rectangle
    private padDown!: Phaser.Geom.Rectangle
    private padLeft!: Phaser.Geom.Rectangle
    private padRight!: Phaser.Geom.Rectangle
	private dpad!: Phaser.GameObjects.Image

	private active!: any
    private currentScene!: Phaser.Scene
    private bg!: Phaser.GameObjects.TileSprite
    private logo!: Phaser.GameObjects.Image
    private showTip = false
    private count = 0

    constructor ()
    {
        super('Controller')

        this.padUp = new Phaser.Geom.Rectangle(23, 0, 32, 26)
        this.padDown = new Phaser.Geom.Rectangle(23, 53, 32, 26)
        this.padLeft = new Phaser.Geom.Rectangle(0, 26, 23, 27)
        this.padRight = new Phaser.Geom.Rectangle(55, 26, 23, 27)
    }

    preload ()
    {
    }

    create ()
    {
        this.textures.addSpriteSheetFromAtlas('mine', { atlas: 'space', frame: 'mine', frameWidth: 64 })
        this.textures.addSpriteSheetFromAtlas('asteroid', { atlas: 'space', frame: 'asteroid', frameWidth: 96 })

        this.anims.create({ key: 'asteroid', frames: this.anims.generateFrameNumbers('asteroid', { start: 0, end: 24 }), frameRate: 12, repeat: -1 })
        this.anims.create({ key: 'mine', frames: this.anims.generateFrameNumbers('mine', { start: 0, end: 15 }), frameRate: 20, repeat: -1 })

        this.bg = this.add.tileSprite(0, 0, 1920, 930, TextureKeys.Universe).setOrigin(0)
        this.logo = this.add.image(1750, 20, TextureKeys.Logo).setOrigin(0).setScale(0.4).setAlpha(0.2)
        
        // panel container background
        let panel_bg = this.add.image(UiLayout.Controller_panelX, UiLayout.Controller_panelY, 'ui', 'panel').setOrigin(0)
        panel_bg.setAlpha(0.5)
        // panel container
        this.panel_container = this.add.container(UiLayout.Controller_panelX, UiLayout.Controller_panelY, [])
        // Buttons
        this.createButton(1, 'SceneA', UiLabels.Tasks, 36, 26)
        this.createButton(2, 'SceneB', UiLabels.PHM, 157, 26)
        this.createButton(3, 'SceneC', UiLabels.DT, 278, 26)
        this.createButton(4, 'SceneD', UiLabels.IoT, 36, 76)
        this.createButton(5, 'SceneE', UiLabels.Equipment, 157, 76)
        this.createButton(6, 'SceneF', UiLabels.Log, 278, 76)
        // Button 1 is active first
        this.button1.setFrame('button-down')
        this.button1.setData('active', true)
        this.active = this.button1
        // Button Labels
        this.add.image(UiLayout.Controller_panelX, UiLayout.Controller_panelY, 'ui', 'scene-labels').setOrigin(0)
        // Toggles
        this.toggle1 = this.createVisibleToggle(902, 35)
        this.toggle2 = this.createActiveToggle(902, 75)
        // LCD
        this.text1 = this.add.bitmapText(520, 42, 'digital', UiLabels.Tasks, 32).setOrigin(0.5, 0).setAlpha(0.8)
        this.text2 = this.add.bitmapText(520, 74, 'digital', UiLabels.IoT, 22).setOrigin(0.5, 0).setAlpha(0.8)
        // D-Pad
        this.createDPad()
        // add controls to the container
        this.panel_container.add([this.button1, this.button2, this.button3, this.button4, this.button5, this.button6])
        this.panel_container.add([this.toggle1, this.toggle2])
        this.panel_container.add([this.text1, this.text2])
        this.panel_container.add(this.dpad)

        // this.scene.launch('SceneA')
        // this.scene.launch('SceneB')
        // this.scene.launch('SceneC')
        // this.scene.launch('SceneD')
        // this.scene.launch('SceneE')
        // this.scene.launch('SceneF')
        // this.currentScene = this.scene.get('SceneA')
        this.createWindow(Mapf)
    }

    createWindow (func)
    {
        var x = Phaser.Math.Between(400, 600);
        var y = Phaser.Math.Between(64, 128);

        var handle = 'window' + this.count++;

        var win = this.add.zone(x, y, func.WIDTH, func.HEIGHT).setInteractive().setOrigin(0);

        var demo = new func(handle, win);

        this.input.setDraggable(win);

        win.on('drag',  (pointer, dragX, dragY) => {
            win.x = dragX
            win.y = dragY
            demo.refresh()
        }, this)

        win.on('pointerup', (pointer, localX, localY) => {
            // bring to top.
            demo.refresh()
            if (localX < 20 && localY < 20) {
                this.scene.remove(handle)
                win.destroy()
            }
        }, this)

        this.scene.add(handle, demo, true);
    }

    createVisibleToggle (x: number, y: number)
    {
        let toggle = this.add.image(x, y, 'ui', 'toggle-on').setOrigin(0)

        toggle.setInteractive()

        toggle.setData('on', true)

        toggle.on('pointerup',  () => {

            if (toggle.getData('on'))
            {
                toggle.setFrame('toggle-off')
                toggle.setData('on', false)
                this.scene.setVisible(false, this.currentScene)
            }
            else
            {
                toggle.setFrame('toggle-on')
                toggle.setData('on', true)
                this.scene.setVisible(true, this.currentScene)
            }

        }, this)

        return toggle
    }

    createActiveToggle (x: number, y: number)
    {
        let toggle = this.add.image(x, y, 'ui', 'toggle-on').setOrigin(0)

        toggle.setInteractive()

        toggle.setData('on', true)

        toggle.on('pointerup',  () => {

            if (toggle.getData('on'))
            {
                toggle.setFrame('toggle-off')
                toggle.setData('on', false)
                this.scene.setActive(false, this.currentScene)

            }
            else
            {
                toggle.setFrame('toggle-on')
                toggle.setData('on', true)
                this.scene.setActive(true, this.currentScene)
            }

        }, this)

        return toggle
    }

    createButton (id: string | number, scene: string, name: string, x: number, y: number)
    {
        let btn = this.add.image(x, y, 'ui', 'button-out').setOrigin(0)

        btn.setInteractive()

        btn.setData('id', id)
        btn.setData('scene', scene)
        btn.setData('name', name)
        btn.setData('active', false)
        
        btn.on('pointerover',  () => {

            if (!btn.getData('active'))
            {
                btn.setFrame('button-over')
            }

        })

        btn.on('pointerout',  () => {

            if (btn.getData('active'))
            {
                btn.setFrame('button-down')
            }
            else
            {
                btn.setFrame('button-out')
            }

        })

        btn.on('pointerup',  () => {

            if (!btn.getData('active'))
            {
                this.setActiveScene(btn)
            }
            let type = btn.getData('name')
            switch (type) {
                case UiLabels.Tasks:
                    this.createWindow(Mapf)
                    break
                case UiLabels.PHM:
                    this.createWindow(Stars)
                    break
                default:
                    break
            }
            

        }, this)

        this['button' + id] = btn
        return btn
    }

    createDPad ()
    {
        this.dpad = this.add.image(670, 26, 'ui', 'nav-out').setOrigin(0)

        this.dpad.setInteractive()

        this.dpad.on('pointermove',  (pointer: any, px: number, py: number) => {

            this.showTip = true

            if (this.padUp.contains(px, py))
            {
                this.dpad.setFrame('nav-up')
                this.updateToolTip('bring to top')
            }
            else if (this.padDown.contains(px, py))
            {
                this.dpad.setFrame('nav-down')
                this.updateToolTip('send to back')
            }
            else if (this.padLeft.contains(px, py))
            {
                this.dpad.setFrame('nav-left')
                this.updateToolTip('move down')
            }
            else if (this.padRight.contains(px, py))
            {
                this.dpad.setFrame('nav-right')
                this.updateToolTip('move up')
            }
            else
            {
                this.dpad.setFrame('nav-out')
                this.showTip = false
            }

        }, this)

        this.dpad.on('pointerout',  () => {

            this.dpad.setFrame('nav-out')
            this.showTip = false

        }, this)

        this.dpad.on('pointerup',  (pointer: any, px: number, py: number) => {

            if (this.padUp.contains(px, py))
            {
                this.scene.bringToTop(this.currentScene)
                this.showTip = false
            }
            else if (this.padDown.contains(px, py))
            {
                this.scene.moveAbove('Controller', this.currentScene)
                this.showTip = false
            }
            else if (this.padLeft.contains(px, py))
            {
                let idx = this.scene.getIndex(this.currentScene)                

                if (idx > 1)
                {
                    this.scene.moveDown(this.currentScene)
                }

                this.showTip = false
            }
            else if (this.padRight.contains(px, py))
            {
                this.scene.moveUp(this.currentScene)
                this.showTip = false
            }

        }, this)
    }

    setActiveScene (btn: Phaser.GameObjects.Image)
    {
        //  De-activate the old one
        this.active.setData('active', false)
        this.active.setFrame('button-out')

        btn.setData('active', true)
        btn.setFrame('button-down')

        this.active = btn
        this.currentScene = this.scene.get(btn.getData('scene'))

        if (this.scene.isVisible(this.currentScene))
        {
            this.toggle1.setFrame('toggle-on')
            this.toggle1.setData('on', true)
        }
        else
        {
            this.toggle1.setFrame('toggle-off')
            this.toggle1.setData('on', false)
        }

        if (this.scene.isActive(this.currentScene))
        {
            this.toggle2.setFrame('toggle-on')
            this.toggle2.setData('on', true)
        }
        else
        {
            this.toggle2.setFrame('toggle-off')
            this.toggle2.setData('on', false)
        }

        this.text1.setText(btn.getData('name'))
    }

    updateToolTip (tip?: string | string[] | undefined)
    {
        if (!tip)
        {
            let idx = this.scene.getIndex(this.currentScene)

            tip = 'index ' + idx + ' / 6'
        }

        this.text2.setText(tip)
    }

    update (time: any, delta: number)
    {
        this.bg.tilePositionX += 0.02 * delta
        this.bg.tilePositionY += 0.005 * delta

        if (!this.showTip)
        {
            this.updateToolTip()
        }
    }

}



/*
class SceneA extends Phaser.Scene {

    constructor ()
    {
        super('SceneA');

        this.nebula;
    }

    create ()
    {
        this.cameras.main.setViewport(0, 136, 1024, 465);

        this.nebula = this.add.image(300, 250, 'space', 'nebula');
    }

    update (time, delta)
    {
        this.nebula.rotation += 0.00006 * delta;
    }

}

class SceneB extends Phaser.Scene {

    constructor ()
    {
        super('SceneB');

        this.sun;
    }

    create ()
    {
        this.cameras.main.setViewport(0, 136, 1024, 465);

        this.sun = this.add.image(900, 80, 'space', 'sun');
    }

    update (time, delta)
    {
        this.sun.x -= 0.02 * delta;
        this.sun.y += 0.015 * delta;

        if (this.sun.y >= 630)
        {
            this.sun.setPosition(1150, -190);
        }
    }

}

class SceneC extends Phaser.Scene {

    constructor ()
    {
        super('SceneC');

        this.asteroids = [];

        this.positions = [
            { x: 37, y: 176 },
            { x: 187, y: 66 },
            { x: 177, y: 406 },
            { x: 317, y: 256 },
            { x: 417, y: -10 },
            { x: 487, y: 336 },
            { x: 510, y: 116 },
            { x: 727, y: 186 },
            { x: 697, y: 10 },
            { x: 597, y: 216 },
            { x: 695, y: 366 },
            { x: 900, y: 76 },
            { x: 1008, y: 315 }
        ];
    }

    create ()
    {
        this.cameras.main.setViewport(0, 136, 1024, 465);

        for (let i = 0; i < this.positions.length; i++)
        {
            let pos = this.positions[i];

            let therock = this.add.sprite(pos.x, pos.y, 'asteroid').play('asteroid');

            therock.setData('vx', 0.04);
            therock.setOrigin(0);
            therock.setScale(Phaser.Math.FloatBetween(0.3, 0.6));

            this.asteroids.push(therock);
        }
    }

    update (time, delta)
    {
        for (let i = 0; i < this.asteroids.length; i++)
        {
            let therock = this.asteroids[i];

            therock.x -= therock.getData('vx') * delta;

            if (therock.x <= -100)
            {
                therock.x = 1224;
            }
        }
    }

}

class SceneD extends Phaser.Scene {

    constructor ()
    {
        super('SceneD');

        this.planet;
    }

    create ()
    {
        this.cameras.main.setViewport(0, 136, 1024, 465);

        this.planet = this.add.image(200, 380, 'space', 'planet');
    }

    update (time, delta)
    {
        this.planet.x += 0.01 * delta;

        if (this.planet.x >= 1224)
        {
            this.planet.x = -200;
        }
    }

}

class SceneE extends Phaser.Scene {

    constructor ()
    {
        super('SceneE');

        this.ship;
        this.particles;
        this.emitter;

        this.splineData = [
            50, 300,
            146, 187,
            35, 94,
            180, 40,
            446, 35,
            438, 100,
            337, 150,
            452, 185,
            560, 155,
            641, 90,
            723, 147,
            755, 262,
            651, 271,
            559, 318,
            620, 384,
            563, 469,
            433, 457,
            385, 395,
            448, 334,
            406, 265,
            316, 305,
            268, 403,
            140, 397,
            205, 309,
            204, 240,
            144, 297,
            50, 300
          ];

        this.curve;
    }

    create ()
    {
        this.cameras.main.setViewport(0, 136, 1024, 465);

        this.curve = new Phaser.Curves.Spline(this.splineData);

        let ship = this.add.follower(this.curve, 50, 300, 'space', 'ship');

        ship.startFollow({
            duration: 12000,
            yoyo: true,
            ease: 'Sine.easeInOut',
            repeat: -1
        });

        this.particles = this.add.particles('space');

        this.emitter = this.particles.createEmitter({
            frame: 'blue',
            speed: 100,
            lifespan: 2000,
            alpha: 0.6,
            angle: 180,
            scale: { start: 0.7, end: 0 },
            blendMode: 'ADD'
        });

        ship.setDepth(1);

        this.ship = ship;

        this.emitter.startFollow(this.ship);
    }

}

class SceneF extends Phaser.Scene {

    constructor ()
    {
        super('SceneF');

        this.mines = [];
    }

    create ()
    {
        this.cameras.main.setViewport(0, 136, 1024, 465);

        for (let i = 0; i < 8; i++)
        {
            let x = Phaser.Math.Between(400, 800);
            let y = Phaser.Math.Between(0, 460);

            let mine = this.add.sprite(x, y, 'mine').play('mine');

            mine.setData('vx', Phaser.Math.FloatBetween(0.08, 0.14));

            this.mines.push(mine);
        }
    }

    update (time, delta)
    {
        for (let i = 0; i < this.mines.length; i++)
        {
            let mine = this.mines[i];

            mine.x -= mine.getData('vx') * delta;

            if (mine.x <= -100)
            {
                mine.x = 1224;
                mine.y = Phaser.Math.Between(0, 460);
            }
        }
    }

}

let config = {
    type: Phaser.AUTO,
    width: 1024,
    height: 600,
    parent: 'phaser-example',
    backgroundColor: '#000000',
    scene: [ Controller, SceneA, SceneB, SceneC, SceneD, SceneE, SceneF ]
};

let game = new Phaser.Game(config);

*/