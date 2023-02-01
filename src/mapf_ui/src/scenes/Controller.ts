import TextureKeys from '~/consts/TextureKeys'
import {UiLabels, UiLayout} from '../consts/UiLabels'
import Stars from './Stars'
import Mapf from './Mapf'
import StoreDetail from './StroeDetail'
import Tasks from './Tasks'
import RightTop from './RightTop'
import { SceneBusKeys } from '~/consts/SceneKeys'
import RightMiddle from './RightMiddle'

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

    private mainwindow?: any

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

        this.mainwindow = this.createWindow(Mapf, 380, 10)
    }

    createWindow (func, x?: number, y?:number)
    {
        if(x === undefined) x = Phaser.Math.Between(0, 200);
        if(y === undefined) y = Phaser.Math.Between(64, 128);

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
        return demo
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
                this.game.config.runPhase = 0
                // this.scene.setVisible(false, this.currentScene)
            }
            else
            {
                toggle.setFrame('toggle-on')
                toggle.setData('on', true)
                this.game.config.runPhase = 1
                // this.scene.setVisible(true, this.currentScene)
                // this.mainwindow.bg.setInteractive()
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
                    this.createWindow(Mapf, 380, 5)
                    break
                case UiLabels.PHM:
                    this.createWindow(Stars,1545, 5)
                    break
                case UiLabels.IoT:
                    this.createWindow(StoreDetail, 5, 5)
                    break
                case UiLabels.Equipment:
                    this.createWindow(Tasks, 1545, 520)
                    break
                case UiLabels.DT:
                    this.registry.set(SceneBusKeys.SetPhase, this.game.config.runPhase) //通知Mapf.ts，更新Agv的不同路段的起点
                    break
                case UiLabels.Log:
                    this.createWindow(RightTop,5,405)
                    this.createWindow(RightMiddle, 5, 795)
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
