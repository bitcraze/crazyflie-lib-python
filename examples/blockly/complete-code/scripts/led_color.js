Blockly.defineBlocksWithJsonArray([
  {
    type: 'led_color',
    message0: 'Set LED color to %1',
    args0: [
      {
        type: 'field_dropdown',
        name: 'COLOR',
        options: [
          ['🔴 Red', 'red'],
          ['🟢 Green', 'green'],
          ['🔵 Blue', 'blue'],
          ['🟡 Yellow', 'yellow'],
          ['🟣 Purple', 'purple'],
          ['🟠 Orange', 'orange'],
          ['🩵 Cyan', 'cyan'],
          ['🤍 White', 'white'],
          ['⚫ Off', 'off']
        ]
      }
    ],
    previousStatement: null,
    nextStatement: null,
    colour: 60,
    tooltip: 'Set the LED ring to a specific color',
    helpUrl: ''
  },
]);

Blockly.Python.forBlock['led_color'] = function (block) {
  const color = block.getFieldValue('COLOR');

  // Map colors to WRGB values (W, R, G, B)
  // W channel is extracted from min(R,G,B) for better brightness
  const colorMap = {
    'red': { w: 0, r: 255, g: 0, b: 0 },
    'green': { w: 0, r: 0, g: 255, b: 0 },
    'blue': { w: 0, r: 0, g: 0, b: 255 },
    'yellow': { w: 0, r: 255, g: 255, b: 0 },
    'purple': { w: 0, r: 128, g: 0, b: 128 },
    'orange': { w: 0, r: 255, g: 165, b: 0 },
    'cyan': { w: 0, r: 0, g: 255, b: 255 },
    'white': { w: 255, r: 0, g: 0, b: 0 },
    'off': { w: 0, r: 0, g: 0, b: 0 }
  };

  const wrgb = colorMap[color];

  // Pack WRGB into uint32 format: 0xWWRRGGBB
  const packed = (wrgb.w << 24) | (wrgb.r << 16) | (wrgb.g << 8) | wrgb.b;

  return `    # Set color LED to ${color}
    if led_param:
        cf.param.set_value(led_param, ${packed})
        time.sleep(0.01)
`;
};
