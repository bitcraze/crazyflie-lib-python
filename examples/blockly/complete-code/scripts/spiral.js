Blockly.defineBlocksWithJsonArray([
  {
    type: 'spiral',
    message0: 'Spiral %1 %2 %3',
    args0: [
      {
        type: 'field_dropdown',
        name: 'SIZE',
        options: [
          ['Small', 'small'],
          ['Medium', 'medium'],
          ['Big', 'big']
        ]
      },
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
        name: 'CLIMB',
        options: [
          ['level', '0.0'],
          ['climbing', '0.5'],
          ['descending', '-0.5']
        ]
      }
    ],
    previousStatement: null,
    nextStatement: null,
    colour: 190,
    tooltip: 'Make the Crazyflie follow a full 360° spiral - use between Takeoff and Land',
    helpUrl: ''
  },
]);

Blockly.Python.forBlock['spiral'] = function (block) {
  const size = block.getFieldValue('SIZE');
  const direction = block.getFieldValue('DIRECTION');
  const climb = block.getFieldValue('CLIMB');

  // Map size to start and end radius
  let startRadius, endRadius;
  switch(size) {
    case 'small':
      startRadius = '0.2';
      endRadius = '0.5';
      break;
    case 'medium':
      startRadius = '0.3';
      endRadius = '0.8';
      break;
    case 'big':
      startRadius = '0.5';
      endRadius = '1.2';
      break;
  }

  // Full 360° spiral
  const angleRad = (2 * Math.PI).toFixed(4);

  // Calculate duration based on average radius
  const avgRadius = (parseFloat(startRadius) + parseFloat(endRadius)) / 2;
  const arcLength = avgRadius * 2 * Math.PI;
  const speed = 0.5; // medium speed
  const duration = (arcLength / speed).toFixed(2);

  // Convert direction and climb
  const clockwise = direction === 'cw' ? 'True' : 'False';

  return `    commander.spiral(${angleRad}, ${startRadius}, ${endRadius}, ${climb}, ${duration}, sideways=False, clockwise=${clockwise})
    time.sleep(${duration})
`;
};
