Blockly.defineBlocksWithJsonArray([
  {
    type: 'altitude',
    message0: 'Move %1 %2 at %3 speed',
    args0: [
      {
        type: 'field_dropdown',
        name: 'DIRECTION',
        options: [
          ['Up ⬆️', 'up'],
          ['Down ⬇️', 'down']
        ]
      },
      {
        type: 'field_dropdown',
        name: 'DISTANCE',
        options: [
          ['0.25m', '0.25'],
          ['0.5m', '0.5'],
          ['0.75m', '0.75'],
          ['1.0m', '1.0'],
          ['1.5m', '1.5'],
          ['2.0m', '2.0']
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
    colour: 260,
    tooltip: 'Move the Crazyflie up or down - use between Takeoff and Land',
    helpUrl: ''
  },
]);

Blockly.Python.forBlock['altitude'] = function (block) {
  const direction = block.getFieldValue('DIRECTION');
  const distance = block.getFieldValue('DISTANCE');
  const speed = block.getFieldValue('SPEED');
  const time = (parseFloat(distance) / parseFloat(speed)).toFixed(2);

  // Positive for up, negative for down
  const zDistance = direction === 'up' ? distance : `-${distance}`;

  return `    # Move vertically (altitude change)
    commander.go_to(0.0, 0.0, ${zDistance}, 0, ${time}, relative=True)
    time.sleep(${time})
`;
};
