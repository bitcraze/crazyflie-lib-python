Blockly.defineBlocksWithJsonArray([
  {
    type: 'takeoff',
    message0: 'Takeoff 🚁',
    nextStatement: null,
    colour: 200,
    tooltip: 'Make the Crazyflie take off to 1.0m height - must be the first block',
    helpUrl: ''
  },
]);

Blockly.Python.forBlock['takeoff'] = function () {
  return '    commander.takeoff(1.0, 2.0, 0)\n    time.sleep(3.0)\n';
};
