Blockly.defineBlocksWithJsonArray([
  {
    type: 'move',
    message0: 'Move %1 %2 at %3 speed',
    args0: [
      {
        type: 'field_dropdown',
        name: 'DIRECTION',
        options: [
          ['Forward ⬆️', 'forward'],
          ['Back ⬇️', 'back'],
          ['Left ⬅️', 'left'],
          ['Right ➡️', 'right']
        ]
      },
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
    colour: 160,
    tooltip: 'Move the Crazyflie in the selected direction - use between Takeoff and Land',
    helpUrl: ''
  },
]);

Blockly.Python.forBlock['move'] = function (block) {
  const direction = block.getFieldValue('DIRECTION');
  const distance = block.getFieldValue('DISTANCE');
  const speed = block.getFieldValue('SPEED');
  const time = (parseFloat(distance) / parseFloat(speed)).toFixed(2);

  let bodyX = '0.0', bodyY = '0.0';

  switch(direction) {
    case 'forward':
      bodyX = distance;
      break;
    case 'back':
      bodyX = `-${distance}`;
      break;
    case 'left':
      bodyY = distance;
      break;
    case 'right':
      bodyY = `-${distance}`;
      break;
  }

  return `    # Transform body-frame to world-frame based on current yaw
    world_x = ${bodyX} * math.cos(current_yaw) - ${bodyY} * math.sin(current_yaw)
    world_y = ${bodyX} * math.sin(current_yaw) + ${bodyY} * math.cos(current_yaw)
    commander.go_to(world_x, world_y, 0.0, 0, ${time}, relative=True)
    time.sleep(${time})
`;
};
