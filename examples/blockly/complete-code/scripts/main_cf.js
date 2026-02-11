/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */
(function () {
  const btn = document.getElementById('play');
  let workspace;

  /**
   * Validates that the program starts with takeoff and ends with land
   */
  function validateProgram() {
    const topBlocks = workspace.getTopBlocks(true);

    if (topBlocks.length === 0) {
      showNotification('Please add some blocks to run!', 'warning');
      return false;
    }

    // Find the main sequence (should be exactly one)
    const mainSequence = topBlocks.find(block => block.type === 'takeoff');

    if (!mainSequence) {
      showNotification('Your program must start with a Takeoff block!', 'error');
      return false;
    }

    // Check if there are other disconnected blocks
    if (topBlocks.length > 1) {
      showNotification('All blocks must be connected to the Takeoff block!', 'warning');
      return false;
    }

    // Walk to the end of the sequence to verify it ends with land
    let currentBlock = mainSequence;
    let lastBlock = currentBlock;

    while (currentBlock) {
      lastBlock = currentBlock;
      currentBlock = currentBlock.getNextBlock();
    }

    if (lastBlock.type !== 'land') {
      showNotification('Your program must end with a Land block!', 'error');
      return false;
    }

    return true;
  }

  /**
   * Handles the play button click event
   * Generates Python code and sends it to the backend
   */
  function handlePlay() {
    // Validate program structure
    if (!validateProgram()) {
      return;
    }

    // Step 1: Preparing
    btn.disabled = true;
    btn.textContent = '⏳\nPreparing...';
    showNotification('Preparing code...', 'success');

    // Generate the full Python code with URI
    const rawBlocklyCode = Blockly.Python.workspaceToCode(workspace);
    const cleaned = rawBlocklyCode
      .replace(/^\n+/, '')
      .replace(/\s+$/, '');
    const dedented = cleaned ? dedent(cleaned) : '';
    const blocklyCode = dedented ? indent(dedented, 4) : '';

    // Get URI from input field
    const uriInput = document.getElementById('crazyflieUri');
    const crazyflieUri = uriInput ? uriInput.value : 'radio://0/80/2M/E7E7E7E7E7';

    const fullCode = PYTHON_TEMPLATE
      .replace('{{BLOCKLY_CODE}}', blocklyCode)
      .replace('{{CRAZYFLIE_URI}}', crazyflieUri);

    // Step 2: Sending code
    setTimeout(() => {
      btn.textContent = '📡\nSending...';
      showNotification('Sending code to Crazyflie...', 'success');

      fetch('/run', {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain' },
        body: fullCode
      })
      .then(response => {
        if (!response.ok) throw new Error('Server error');

        // Step 3: Code sent successfully
        btn.textContent = '✓\nSent!';
        showNotification('Code sent! Crazyflie is executing...', 'success');
        console.log('Sent to backend');

        // Keep success state for 2 seconds before re-enabling
        setTimeout(() => {
          btn.disabled = false;
          btn.textContent = '▶\nFLY!';
        }, 2000);
      })
      .catch(err => {
        // Step 3b: Error state
        btn.textContent = '✗\nFailed';
        showNotification('Error: ' + err.message, 'error');
        console.error(err);

        // Re-enable after showing error for 2 seconds
        setTimeout(() => {
          btn.disabled = false;
          btn.textContent = '▶\nFLY!';
        }, 2000);
      });
    }, 500);
  }

  /**
   * Shows a temporary notification to the user
   */
  function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.textContent = message;
    notification.style.cssText = `
      position: fixed;
      top: 100px;
      right: 20px;
      padding: 15px 25px;
      background: ${type === 'success' ? '#95C941' : type === 'error' ? '#e74c3c' : '#f39c12'};
      color: white;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      font-weight: 700;
      z-index: 1000;
      animation: slideIn 0.3s ease;
    `;
    document.body.appendChild(notification);

    setTimeout(() => {
      notification.style.animation = 'slideOut 0.3s ease';
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  /**
   * Python script template
   */
  const PYTHON_TEMPLATE = `import argparse
import time
import math

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper
from cflib.utils.reset_estimator import reset_estimator

# URI to the Crazyflie to connect to
uri = uri_helper.uri_from_env(default='{{CRAZYFLIE_URI}}')

def run_sequence(cf):
    commander = cf.high_level_commander

    # Detect color LED deck (bottom or top)
    led_param = None
    try:
        if 'bcColorLedBot' in cf.param.toc.toc['deck'] and str(cf.param.get_value('deck.bcColorLedBot')) == '1':
            led_param = 'colorLedBot.wrgb8888'
            print('Detected bottom-facing color LED deck')
        elif 'bcColorLedTop' in cf.param.toc.toc['deck'] and str(cf.param.get_value('deck.bcColorLedTop')) == '1':
            led_param = 'colorLedTop.wrgb8888'
            print('Detected top-facing color LED deck')
        else:
            print('No color LED deck detected - LED commands will be skipped')
    except (KeyError, AttributeError):
        print('No color LED deck detected - LED commands will be skipped')

    # Arm the Crazyflie
    cf.platform.send_arming_request(True)
    time.sleep(1.0)

    # Track current yaw for body-frame movements
    current_yaw = 0.0

{{BLOCKLY_CODE}}

    time.sleep(5)
    commander.stop()


if __name__ == '__main__':
    cflib.crtp.init_drivers()

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        cf = scf.cf
        reset_estimator(cf)
        run_sequence(cf)
`;

function indent(code, spaces = 4) {
  const pad = ' '.repeat(spaces);
  return code
    .split('\n')
    .map(line => line.trim() ? pad + line : line)
    .join('\n');
}

// Remove common leading indentation from code (like Python's textwrap.dedent)
function dedent(code) {
  const lines = code.split('\n');
  let minIndent = Infinity;
  for (const line of lines) {
    if (line.trim() === '') continue;
    const m = line.match(/^[ \t]*/);
    if (m) minIndent = Math.min(minIndent, m[0].length);
  }
  if (!isFinite(minIndent) || minIndent === 0) return code;
  return lines.map(line => line.startsWith(' '.repeat(minIndent)) ? line.slice(minIndent) : line.replace(/^[ \t]+/, '')).join('\n');
}

function updateCodePreview() {
  // Get generated code but DO NOT trim leading spaces — we need them for dedent()
  const rawBlocklyCode = Blockly.Python.workspaceToCode(workspace);
  // Remove only trailing whitespace/newlines and any leading empty lines
  const cleaned = rawBlocklyCode
    .replace(/^\n+/, '')    // drop leading blank lines, keep leading spaces
    .replace(/\s+$/, '');   // drop trailing whitespace/newlines

  // Remove common leading indentation first, then add one desired outer indent level
  const dedented = cleaned ? dedent(cleaned) : '';

  const blocklyCode = dedented
    ? indent(dedented, 4)
    : '    # Your Blockly code will appear here...\n';

  // Get URI from input field
  const uriInput = document.getElementById('crazyflieUri');
  const crazyflieUri = uriInput ? uriInput.value : 'radio://0/80/2M/E7E7E7E7E7';

  const fullCode = PYTHON_TEMPLATE
    .replace('{{BLOCKLY_CODE}}', blocklyCode)
    .replace('{{CRAZYFLIE_URI}}', crazyflieUri);

  const codeElement = document.querySelector('#codeOutput code');
  codeElement.innerHTML = highlightPython(fullCode);
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function highlightPython(code) {
  // Escape HTML first
  const escaped = escapeHtml(code);

  // Collect strings and comments so we don't highlight inside them
  const stringPattern = /(['"])(?:(?=(\\?))\2.)*?\1/g;
  const commentPattern = /(#.*$)/gm;

  const strings = [];
  const comments = [];

  // Replace strings with placeholders
  const noStrings = escaped.replace(stringPattern, (m) => {
    const i = strings.length;
    strings.push(`<span class="code-string">${m}</span>`);
    return `___STR_${i}___`;
  });

  // Replace comments with placeholders
  const noComments = noStrings.replace(commentPattern, (m) => {
    const i = comments.length;
    comments.push(`<span class="code-comment">${m}</span>`);
    return `___COM_${i}___`;
  });

  // Highlight keywords, numbers, functions on the remaining text
  let out = noComments
    .replace(/\b(import|from|def|class|if|elif|else|for|while|return|with|as|True|False|None)\b/g,
      '<span class="code-keyword">$1</span>')
    .replace(/(?<!\w)(\d+(\.\d+)?)(?!\w)/g,
      '<span class="code-number">$1</span>')
    .replace(/\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(?=\()/g,
      '<span class="code-function">$1</span>');

  // Restore comment placeholders
  out = out.replace(/___COM_(\d+)___/g, (_, idx) => comments[Number(idx)]);

  // Restore string placeholders
  out = out.replace(/___STR_(\d+)___/g, (_, idx) => strings[Number(idx)]);

  return out;
}



  /**
   * Helper function to process a single block and return command data
   */
  function processBlock(block) {
    const command = { type: block.type };

    // Handle combined move block
    if (block.type === 'move') {
      const directionField = block.getField('DIRECTION');
      const distanceField = block.getField('DISTANCE');

      if (directionField) {
        command.type = directionField.getValue();
      }
      if (distanceField) {
        command.distance = parseFloat(distanceField.getValue());
      } else {
        command.distance = 0.5;
      }
    }
    // Handle rotate block
    else if (block.type === 'rotate') {
      const directionField = block.getField('DIRECTION');
      const angleField = block.getField('ANGLE');

      command.angle = angleField ? parseFloat(angleField.getValue()) : 90;
      command.direction = directionField ? directionField.getValue() : 'cw';
    }
    // Handle altitude block
    else if (block.type === 'altitude') {
      const directionField = block.getField('DIRECTION');
      const distanceField = block.getField('DISTANCE');

      command.direction = directionField ? directionField.getValue() : 'up';
      command.distance = distanceField ? parseFloat(distanceField.getValue()) : 0.5;
    }
    // Handle spiral block
    else if (block.type === 'spiral') {
      const sizeField = block.getField('SIZE');
      const directionField = block.getField('DIRECTION');
      const climbField = block.getField('CLIMB');

      const size = sizeField ? sizeField.getValue() : 'medium';

      // Map size to start and end radius
      let startRadius, endRadius;
      switch(size) {
        case 'small':
          startRadius = 0.2;
          endRadius = 0.5;
          break;
        case 'medium':
          startRadius = 0.3;
          endRadius = 0.8;
          break;
        case 'big':
          startRadius = 0.5;
          endRadius = 1.2;
          break;
        default:
          startRadius = 0.3;
          endRadius = 0.8;
      }

      command.angle = 360; // Always full spiral
      command.direction = directionField ? directionField.getValue() : 'ccw';
      command.startRadius = startRadius;
      command.endRadius = endRadius;
      command.ascent = climbField ? parseFloat(climbField.getValue()) : 0.0;
      command.sideways = false; // Always forward
    }
    // Handle LED color block
    else if (block.type === 'led_color') {
      const colorField = block.getField('COLOR');
      command.color = colorField ? colorField.getValue() : 'off';
    }
    // Support legacy individual movement blocks for backward compatibility
    else if (['forward', 'back', 'left', 'right'].includes(block.type)) {
      const distanceField = block.getField('DISTANCE');
      if (distanceField) {
        command.distance = parseFloat(distanceField.getValue());
      } else {
        command.distance = 0.5;
      }
    }

    return command;
  }

  /**
   * Helper function to process blocks recursively
   */
  function processBlockChain(startBlock) {
    const commands = [];
    let currentBlock = startBlock;

    while (currentBlock) {
      // Handle repeat block
      if (currentBlock.type === 'repeat') {
        const timesField = currentBlock.getField('TIMES');
        const times = timesField ? parseInt(timesField.getValue()) : 2;

        // Get the blocks inside the repeat
        const doBlock = currentBlock.getInputTargetBlock('DO');
        if (doBlock) {
          // Process the inner blocks
          const innerCommands = processBlockChain(doBlock);

          // Repeat them the specified number of times
          for (let i = 0; i < times; i++) {
            commands.push(...innerCommands);
          }
        }
      } else {
        // Regular block - process it
        commands.push(processBlock(currentBlock));
      }

      currentBlock = currentBlock.getNextBlock();
    }

    return commands;
  }

  /**
   * Extracts command sequence from workspace blocks
   */
  function getCommandSequence() {
    const topBlocks = workspace.getTopBlocks(true);
    const mainSequence = topBlocks.find(block => block.type === 'takeoff');

    if (!mainSequence) return [];

    return processBlockChain(mainSequence);
  }

  /**
   * Handles the simulate button click event
   */
  function handleSimulate() {
    // Validate program structure
    if (!validateProgram()) {
      return;
    }

    const commands = getCommandSequence();

    if (commands.length === 0) {
      showNotification('No commands to simulate!', 'warning');
      return;
    }

    // Disable button during simulation
    const simulateBtn = document.getElementById('simulateBtn');
    simulateBtn.disabled = true;
    simulateBtn.textContent = '⏸\nRunning...';

    // Run simulation
    flightSimulator.simulate(commands).then(() => {
      showNotification('Simulation complete!', 'success');
      simulateBtn.disabled = false;
      simulateBtn.textContent = '▶\nSimulate';
    }).catch(err => {
      showNotification('Simulation error: ' + err.message, 'error');
      simulateBtn.disabled = false;
      simulateBtn.textContent = '▶\nSimulate';
    });
  }

  /**
   * Copies code to clipboard
   */
  function copyCodeToClipboard() {
    // Generate the full Python code with URI
    const rawBlocklyCode = Blockly.Python.workspaceToCode(workspace);

    if (!rawBlocklyCode.trim()) {
      showNotification('No code to copy!', 'warning');
      return;
    }

    const cleaned = rawBlocklyCode
      .replace(/^\n+/, '')
      .replace(/\s+$/, '');
    const dedented = cleaned ? dedent(cleaned) : '';
    const blocklyCode = dedented ? indent(dedented, 4) : '';

    // Get URI from input field
    const uriInput = document.getElementById('crazyflieUri');
    const crazyflieUri = uriInput ? uriInput.value : 'radio://0/80/2M/E7E7E7E7E7';

    const fullCode = PYTHON_TEMPLATE
      .replace('{{BLOCKLY_CODE}}', blocklyCode)
      .replace('{{CRAZYFLIE_URI}}', crazyflieUri);

    navigator.clipboard.writeText(fullCode).then(() => {
      showNotification('Code copied to clipboard!', 'success');

      // Visual feedback on button
      const copyBtn = document.getElementById('copyCode');
      const originalText = copyBtn.textContent;
      copyBtn.textContent = '✓ Copied!';
      copyBtn.style.background = 'rgba(149, 201, 65, 0.2)';

      setTimeout(() => {
        copyBtn.textContent = originalText;
        copyBtn.style.background = 'transparent';
      }, 2000);
    }).catch(err => {
      showNotification('Failed to copy code', 'error');
      console.error('Copy failed:', err);
    });
  }

  /**
   * Enables Blockly mode and sets up event listeners
   */
  function enableBlocklyMode() {
    document.body.setAttribute('mode', 'blockly');
    btn.addEventListener('click', handlePlay);

    // Set up simulate button
    const simulateBtn = document.getElementById('simulateBtn');
    simulateBtn.addEventListener('click', handleSimulate);

    // Set up copy button
    const copyBtn = document.getElementById('copyCode');
    copyBtn.addEventListener('click', copyCodeToClipboard);

    // Set up URI input listener
    const uriInput = document.getElementById('crazyflieUri');
    if (uriInput) {
      // Load saved URI from localStorage
      const savedUri = localStorage.getItem('crazyflieUri');
      if (savedUri) {
        uriInput.value = savedUri;
      }

      // Update code preview and save to localStorage on input
      uriInput.addEventListener('input', () => {
        localStorage.setItem('crazyflieUri', uriInput.value);
        updateCodePreview();
      });
    }

    // Update code preview on workspace changes
    workspace.addChangeListener(updateCodePreview);

    // Initial preview update
    updateCodePreview();
  }

  /**
   * Toolbox configuration with categorized blocks
   */
  const toolbox = {
    kind: 'categoryToolbox',
    contents: [
      {
        kind: 'category',
        name: '🚀 Start/End',
        colour: '200',
        contents: [
          {
            kind: 'label',
            text: 'Always start with:'
          },
          { kind: 'block', type: 'takeoff' },
          {
            kind: 'label',
            text: 'Always end with:'
          },
          { kind: 'block', type: 'land' },
        ]
      },
      {
        kind: 'category',
        name: '🔄 Control',
        colour: '330',
        contents: [
          { kind: 'block', type: 'repeat' }
        ]
      },
      {
        kind: 'category',
        name: '✈️ Movement',
        colour: '120',
        contents: [
          { kind: 'block', type: 'move' },
          { kind: 'block', type: 'rotate' },
          { kind: 'block', type: 'altitude' },
          { kind: 'block', type: 'spiral' }
        ]
      },
      {
        kind: 'category',
        name: '💡 LED',
        colour: '60',
        contents: [
          { kind: 'block', type: 'led_color' }
        ]
      }
    ]
  };

  /**
   * Enhanced workspace configuration with dark theme
   */
  workspace = Blockly.inject('blocklyDiv', {
    toolbox: toolbox,

    // Dark theme for coder aesthetic
    theme: Blockly.Theme.defineTheme('coder_dark', {
      'base': Blockly.Themes.Classic,
      'componentStyles': {
        'workspaceBackgroundColour': '#1e1e1e',
        'toolboxBackgroundColour': '#252526',
        'toolboxForegroundColour': '#95C941',
        'flyoutBackgroundColour': '#252526',
        'flyoutForegroundColour': '#ccc',
        'flyoutOpacity': 0.95,
        'scrollbarColour': '#95C941',
        'insertionMarkerColour': '#95C941',
        'insertionMarkerOpacity': 0.5,
        'scrollbarOpacity': 0.6,
        'cursorColour': '#95C941',
      }
    }),

    // Grid configuration for better alignment
    grid: {
      spacing: 20,
      length: 3,
      colour: '#333',
      snap: true
    },

    // Zoom controls
    zoom: {
      controls: true,
      wheel: true,
      startScale: 1.0,
      maxScale: 3,
      minScale: 0.3,
      scaleSpeed: 1.2
    },

    // Trash can for deleting blocks
    trashcan: true,

    // Scrollbars for large workspaces
    scrollbars: true,

    // Better visual rendering
    renderer: 'zelos',

    // Toolbox position
    toolboxPosition: 'start',
    horizontalLayout: false,

    // Move options
    move: {
      scrollbars: true,
      drag: true,
      wheel: true
    }
  });

  // Add CSS for animations
  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideIn {
      from {
        transform: translateX(400px);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }
    @keyframes slideOut {
      from {
        transform: translateX(0);
        opacity: 1;
      }
      to {
        transform: translateX(400px);
        opacity: 0;
      }
    }
  `;
  document.head.appendChild(style);

  enableBlocklyMode();

})();
