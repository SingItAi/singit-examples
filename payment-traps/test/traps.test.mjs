import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { cases, runScenario, markdown } from '../src/run.mjs';

const results = [];
for (const { trap, network } of cases) {
  test(`${trap.type}: ${trap.scenario}${network ? ` (${network})` : ''}`, async () => {
    results.push(await runScenario(trap, network));
  });
}
test('README mapping exactly matches the observed report', async () => {
  const readme = await readFile(new URL('../README.md', import.meta.url), 'utf8');
  const table = readme.split('<!-- report:start -->\n')[1]?.split('\n<!-- report:end -->')[0];
  assert.equal(results.length, cases.length);
  assert.equal(table, markdown(results));
});
