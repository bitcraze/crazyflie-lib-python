Blockly.defineBlocksWithJsonArray([
  {
    type: 'repeat',
    message0: 'Repeat %1 times',
    args0: [
      {
        type: 'field_dropdown',
        name: 'TIMES',
        options: [
          ['2', '2'],
          ['3', '3'],
          ['4', '4'],
          ['5', '5'],
          ['10', '10']
        ]
      }
    ],
    message1: 'Do %1',
    args1: [
      {
        type: 'input_statement',
        name: 'DO'
      }
    ],
    previousStatement: null,
    nextStatement: null,
    colour: 330,
    tooltip: 'Repeat a sequence of movements multiple times',
    helpUrl: ''
  },
]);

Blockly.Python.forBlock['repeat'] = function (block) {
  const times = block.getFieldValue('TIMES');
  const branch = Blockly.Python.statementToCode(block, 'DO');

  if (!branch) {
    return '';
  }

  return `    # Repeat ${times} times\n    for _ in range(${times}):\n${branch}`;
};
