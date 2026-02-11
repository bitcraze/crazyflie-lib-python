/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */
(function () {
  const btn = document.getElementById('play');

  function handlePlay() {
    let code = javascript.javascriptGenerator.workspaceToCode(
      Blockly.getMainWorkspace(),
    );
    code += 'MusicMaker.play();';
    // Eval can be dangerous. For more controlled execution, check
    // https://github.com/NeilFraser/JS-Interpreter.
    try {
      eval(code);
    } catch (error) {
      console.log(error);
    }
  }

  function enableBlocklyMode() {
    document.body.setAttribute('mode', 'blockly');
    btn.addEventListener('click', handlePlay);
  }

  const toolbox = {
    kind: 'flyoutToolbox',
    contents: [
      {
        kind: 'block',
        type: 'controls_repeat_ext',
        inputs: {
          TIMES: {
            shadow: {
              type: 'math_number',
              fields: {
                NUM: 5,
              },
            },
          },
        },
      },
      {
        kind: 'block',
        type: 'play_sound',
      },
    ],
  };

  Blockly.inject('blocklyDiv', {
    toolbox: toolbox,
    scrollbars: false,
    horizontalLayout: true,
    toolboxPosition: 'end',
  });

  enableBlocklyMode();

})();
