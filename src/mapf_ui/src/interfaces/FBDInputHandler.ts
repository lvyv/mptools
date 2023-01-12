export class FBDInputHandler {
  // The any in the dictionary signature is because 
  // Phaser.Input.Keyboard.KeyCodes is a namespace and cannot be assigned as
  // a type (as far as I know).
  private mappings: any;

  constructor(scene: Phaser.Scene, inputMappings: { [key: string]: any }) {
      this.mappings = {};
      for (const key in inputMappings) {
          let vals = [];
          for (let i = 0; i < inputMappings[key].length; i++) {
              vals.push(scene.input.keyboard.addKey(inputMappings[key][i]));
          }
          this.mappings[key] = vals;
      }
  }

  isJustDown(key: string): boolean {
      for (let i = 0; i < this.mappings[key].length; i++) {
          if (Phaser.Input.Keyboard.JustDown(this.mappings[key][i])) 
              return true;
      }
      return false;
  }

  isDown(key: string): boolean {
      for (let i = 0; i < this.mappings[key].length; i++) {
          if (this.mappings[key][i].isDown) return true;
      }
      return false;
  }
}