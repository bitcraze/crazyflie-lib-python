Blockly.defineBlocksWithJsonArray([
  {
    type: 'right',
    message0: 'Move Right ➡️ %1 at %2 speed',
    args0: [
      {
        type: 'field_dropdown',
        name: 'DISTANCE',
        options: [
          ['0.5m', '0.5'],
          ['1.0m', '1.0'],
          ['1.5m', '1.5'],
          ['2.0m', '2.0'],
          ['2.5m', '2.5'],
          ['3.0m', '3.0']
        ]
      },
      {
        type: 'field_dropdown',
        name: 'SPEED',
        options: [
          ['slow', '0.2'],
          ['medium', '0.5'],
          ['fast', '1.0']
        ]
      }
    ],
    previousStatement: null,
    nextStatement: null,
    colour: 30,
    tooltip: 'Move the Crazyflie right - use between Takeoff and Land',
    helpUrl: ''
  },
]);

Blockly.Python.forBlock['right'] = function (block) {
  const distance = block.getFieldValue('DISTANCE');
  const speed = block.getFieldValue('SPEED');
  const time = (parseFloat(distance) / parseFloat(speed)).toFixed(2);
  return `    # Transform body-frame to world-frame based on current yaw
    world_x = ${distance} * math.sin(current_yaw)
    world_y = -${distance} * math.cos(current_yaw)
    commander.go_to(world_x, world_y, 0.0, 0, ${time}, relative=True)
    time.sleep(${time})
`;
};
