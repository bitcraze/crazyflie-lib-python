Blockly.defineBlocksWithJsonArray([
  {
    type: 'rotate',
    message0: 'Rotate %1 %2°',
    args0: [
      {
        type: 'field_dropdown',
        name: 'DIRECTION',
        options: [
          ['↻ Clockwise', 'cw'],
          ['↺ Counter-Clockwise', 'ccw']
        ]
      },
      {
        type: 'field_dropdown',
        name: 'ANGLE',
        options: [
          ['45', '45'],
          ['90', '90'],
          ['135', '135'],
          ['180', '180'],
          ['270', '270'],
          ['360', '360']
        ]
      }
    ],
    previousStatement: null,
    nextStatement: null,
    colour: 280,
    tooltip: 'Rotate the Crazyflie by changing yaw - use between Takeoff and Land',
    helpUrl: ''
  },
]);

Blockly.Python.forBlock['rotate'] = function (block) {
  const direction = block.getFieldValue('DIRECTION');
  const angle = block.getFieldValue('ANGLE');

  // Fixed rotation speed (90 degrees per second)
  const speed = 90;
  const time = (parseFloat(angle) / speed).toFixed(2);

  // Convert angle to radians and determine direction
  const angleRad = (parseFloat(angle) * Math.PI / 180).toFixed(4);
  const yawChange = direction === 'cw' ? `-${angleRad}` : angleRad;

  return `    # Rotate and update current yaw
    commander.go_to(0.0, 0.0, 0.0, ${yawChange}, ${time}, relative=True)
    current_yaw += ${yawChange}
    time.sleep(${time})
`;
};
