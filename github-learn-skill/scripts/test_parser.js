const fs = require('fs');
const path = require('path');
const parser = require('@babel/parser');

const filePath = 'c:\\Users\\yuff.DESKTOP-55AUCJG\\Desktop\\qwen-code\\packages\\core\\index.ts';
const code = fs.readFileSync(filePath, 'utf-8');

console.log('File content preview:', code.substring(0, 200));
console.log('---');

const ast = parser.parse(code, {
  sourceType: 'module',
  plugins: ['jsx', 'typescript']
});

console.log('AST body types:');
ast.program.body.forEach(node => {
  console.log('  Node type:', node.type);
  if (node.type === 'ExportAllDeclaration') {
    console.log('    -> ExportAllDeclaration source:', node.source?.value);
  }
});