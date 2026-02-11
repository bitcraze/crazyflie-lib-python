Blockly.defineBlocksWithJsonArray([
  {
    type: 'land',
    message0: 'Land 🛬',
    previousStatement: null,
    colour: 200,
    tooltip: 'Land the Crazyflie safely - must be the last block',
    helpUrl: ''
  },
]);

Blockly.Python.forBlock['land'] = function () {
  return '    commander.land(0.0, 2.0)\n    time.sleep(2.0)\n';
};
