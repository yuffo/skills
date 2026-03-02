#!/usr/bin/env node
/**
 * JavaScript/TypeScript 代码骨架分析器
 * 使用 @babel/parser 解析 AST
 *
 * 用法: node js_analyzer.js <文件路径>
 */

const fs = require('fs');
const path = require('path');

// 动态加载 babel parser（如果没安装会提示）
let parser;
try {
  parser = require('@babel/parser');
} catch (e) {
  console.error('错误: 未找到 @babel/parser');
  console.error('请在 scripts 目录下运行: npm install @babel/parser');
  process.exit(1);
}

function getTypeAnnotation(node) {
  if (!node) return '';

  if (node.type === 'TSTypeAnnotation' && node.typeAnnotation) {
    const ta = node.typeAnnotation;
    if (ta.type === 'TSStringKeyword') return 'string';
    if (ta.type === 'TSNumberKeyword') return 'number';
    if (ta.type === 'TSBooleanKeyword') return 'boolean';
    if (ta.type === 'TSAnyKeyword') return 'any';
    if (ta.type === 'TSVoidKeyword') return 'void';
    if (ta.type === 'TSArrayType') return `${getTypeAnnotation(ta.elementType)}[]`;
    if (ta.type === 'TSTypeReference' && ta.typeName) {
      return ta.typeName.name || '';
    }
    if (ta.type === 'TSUnionType' && ta.types) {
      return ta.types.map(getTypeAnnotation).join(' | ');
    }
  }
  return '';
}

function formatParams(params) {
  return params.map(param => {
    let result = param.name;

    if (param.typeAnnotation) {
      const type = getTypeAnnotation(param);
      if (type) result += `: ${type}`;
    }

    if (param.default) {
      result += ' = ...';
    }

    return result;
  }).join(', ');
}

function analyzeFunction(node, className = null) {
  const name = node.id?.name || node.key?.name || 'anonymous';
  const params = formatParams(node.params || []);
  let sig = `${name}(${params})`;

  if (node.returnType) {
    const returnType = getTypeAnnotation(node.returnType);
    if (returnType) sig += ` -> ${returnType}`;
  } else if (node.async) {
    sig += ' -> Promise';
  }

  return sig;
}

function analyzeClass(node) {
  const name = node.id?.name || 'Anonymous';
  const superClass = node.superClass?.name || '';

  const methods = [];
  const properties = [];

  node.body?.body?.forEach(member => {
    if (member.type === 'ClassMethod' || member.type === 'ClassPrivateMethod') {
      const isAsync = member.async ? 'async ' : '';
      const isStatic = member.static ? 'static ' : '';
      const methodName = member.key?.name || member.key?.id?.name || 'unknown';
      const params = formatParams(member.params || []);

      let sig = `${isStatic}${isAsync}${methodName}(${params})`;

      if (member.returnType) {
        const returnType = getTypeAnnotation(member.returnType);
        if (returnType) sig += ` -> ${returnType}`;
      }

      methods.push(sig);
    } else if (member.type === 'ClassProperty' || member.type === 'ClassPrivateProperty') {
      const propName = member.key?.name || 'unknown';
      let prop = propName;

      if (member.typeAnnotation) {
        const type = getTypeAnnotation(member.typeAnnotation);
        if (type) prop += `: ${type}`;
      }

      if (member.value) {
        prop += ' = ...';
      }

      properties.push(prop);
    }
  });

  return { name, superClass, methods, properties };
}

function analyzeFile(filePath) {
  try {
    const code = fs.readFileSync(filePath, 'utf-8');
    const ext = path.extname(filePath);

    const isTS = ext === '.ts' || ext === '.tsx';
    const isJSX = ext === '.jsx' || ext === '.tsx';

    const ast = parser.parse(code, {
      sourceType: 'module',
      plugins: [
        'jsx',
        'typescript',
        'decorators-legacy',
        'classProperties',
        'asyncGenerators',
        'dynamicImport',
        'optionalChaining',
        'nullishCoalescingOperator'
      ]
    });

    const result = {
      file: filePath,
      type: isTS ? 'TypeScript' : 'JavaScript',
      imports: [],
      exports: [],
      classes: [],
      functions: [],
      interfaces: [],
      typeAliases: []
    };

    ast.program.body.forEach(node => {
      // 导入
      if (node.type === 'ImportDeclaration') {
        const source = node.source?.value || '';
        const specifiers = node.specifiers?.map(s => {
          if (s.type === 'ImportDefaultSpecifier') return s.local?.name;
          if (s.type === 'ImportSpecifier') return s.local?.name;
          if (s.type === 'ImportNamespaceSpecifier') return `* as ${s.local?.name}`;
          return '';
        }).filter(Boolean);

        if (specifiers.length > 0) {
          result.imports.push(`${specifiers.join(', ')} from "${source}"`);
        } else {
          result.imports.push(`"${source}"`);
        }
      }

      // 类定义
      if (node.type === 'ClassDeclaration' || node.type === 'ClassExpression') {
        result.classes.push(analyzeClass(node));
      }

      // 函数定义
      if (node.type === 'FunctionDeclaration' && node.id) {
        result.functions.push(analyzeFunction(node));
      }

      // 导出
      if (node.type === 'ExportNamedDeclaration' || node.type === 'ExportDefaultDeclaration') {
        if (node.declaration) {
          if (node.declaration.type === 'ClassDeclaration') {
            result.classes.push(analyzeClass(node.declaration));
            result.exports.push(node.declaration.id?.name);
          } else if (node.declaration.type === 'FunctionDeclaration') {
            result.functions.push(analyzeFunction(node.declaration));
            result.exports.push(node.declaration.id?.name);
          }
        }
        // 处理 export { xxx } from '...' 或 export { xxx }
        if (node.specifiers && node.specifiers.length > 0) {
          const names = node.specifiers.map(s => s.exported?.name || s.local?.name).filter(Boolean);
          if (names.length > 0) {
            const source = node.source?.value ? ` from "${node.source.value}"` : '';
            result.exports.push(`{ ${names.join(', ')} }${source}`);
          }
        }
      }

      // 处理 export * from '...'
      if (node.type === 'ExportAllDeclaration') {
        const source = node.source?.value || '';
        result.exports.push(`* from "${source}"`);
      }

      // TypeScript 特有
      if (isTS) {
        // 接口
        if (node.type === 'TSInterfaceDeclaration') {
          const name = node.id?.name || 'Anonymous';
          const properties = [];

          node.body?.body?.forEach(member => {
            if (member.type === 'TSPropertySignature' && member.key) {
              const propName = member.key.name || '';
              let prop = propName;

              if (member.typeAnnotation) {
                const type = getTypeAnnotation(member.typeAnnotation);
                if (type) prop += `: ${type}`;
              }

              if (member.optional) {
                prop += '?';
              }

              properties.push(prop);
            }
          });

          result.interfaces.push({ name, properties });
        }

        // 类型别名
        if (node.type === 'TSTypeAliasDeclaration') {
          const name = node.id?.name || 'Anonymous';
          result.typeAliases.push(name);
        }
      }
    });

    return result;

  } catch (error) {
    return { file: filePath, error: error.message };
  }
}

function generateOutput(result) {
  const lines = [`# 文件: ${result.file} (${result.type || 'JavaScript'})\n`];

  if (result.error) {
    lines.push(`错误: ${result.error}`);
    return lines.join('\n');
  }

  // 导入
  if (result.imports && result.imports.length > 0) {
    lines.push('## 导入');
    result.imports.slice(0, 15).forEach(imp => lines.push(`  ${imp}`));
    if (result.imports.length > 15) {
      lines.push(`  ... 还有 ${result.imports.length - 15} 个`);
    }
    lines.push('');
  }

  // 导出
  if (result.exports && result.exports.length > 0) {
    lines.push('## 导出');
    result.exports.slice(0, 20).forEach(exp => lines.push(`  ${exp}`));
    if (result.exports.length > 20) {
      lines.push(`  ... 还有 ${result.exports.length - 20} 个`);
    }
    lines.push('');
  }

  // 类型别名
  if (result.typeAliases && result.typeAliases.length > 0) {
    lines.push('## 类型别名');
    result.typeAliases.forEach(t => lines.push(`  type ${t}`));
    lines.push('');
  }

  // 接口
  if (result.interfaces && result.interfaces.length > 0) {
    lines.push('## 接口');
    result.interfaces.forEach(iface => {
      lines.push(`  interface ${iface.name}`);
      if (iface.properties) {
        iface.properties.slice(0, 10).forEach(prop => {
          lines.push(`    - ${prop}`);
        });
        if (iface.properties.length > 10) {
          lines.push(`    ... 还有 ${iface.properties.length - 10} 个属性`);
        }
      }
    });
    lines.push('');
  }

  // 类
  if (result.classes && result.classes.length > 0) {
    result.classes.forEach(cls => {
      let classLine = `## 类: ${cls.name}`;
      if (cls.superClass) {
        classLine += ` extends ${cls.superClass}`;
      }
      lines.push(classLine);

      if (cls.properties && cls.properties.length > 0) {
        lines.push('  属性:');
        cls.properties.slice(0, 8).forEach(prop => {
          lines.push(`    - ${prop}`);
        });
        if (cls.properties.length > 8) {
          lines.push(`    ... 还有 ${cls.properties.length - 8} 个属性`);
        }
      }

      if (cls.methods && cls.methods.length > 0) {
        lines.push('  方法:');
        cls.methods.slice(0, 15).forEach(method => {
          lines.push(`    - ${method}`);
        });
        if (cls.methods.length > 15) {
          lines.push(`    ... 还有 ${cls.methods.length - 15} 个方法`);
        }
      }
      lines.push('');
    });
  }

  // 顶层函数
  if (result.functions && result.functions.length > 0) {
    lines.push('## 顶层函数');
    result.functions.slice(0, 20).forEach(func => {
      lines.push(`  - ${func}`);
    });
    if (result.functions.length > 20) {
      lines.push(`  ... 还有 ${result.functions.length - 20} 个函数`);
    }
    lines.push('');
  }

  return lines.join('\n');
}

// 主函数
function main() {
  const args = process.argv.slice(2);

  if (args.length < 1) {
    console.log('用法: node js_analyzer.js <JS/TS文件路径>');
    console.log('示例: node js_analyzer.js ./src/index.ts');
    process.exit(1);
  }

  const filePath = path.resolve(args[0]);

  if (!fs.existsSync(filePath)) {
    console.error(`错误: 文件不存在: ${filePath}`);
    process.exit(1);
  }

  const result = analyzeFile(filePath);
  const output = generateOutput(result);
  console.log(output);
}

main();