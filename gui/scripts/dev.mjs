// Wrapper around `vite` that scrubs ELECTRON_RUN_AS_NODE from the env
// before launching. If that variable is set in the parent shell (it is
// in this dev box), Electron starts as plain Node, which makes
// require('electron') return a string and `app` undefined.
import { spawn } from 'node:child_process'

const env = { ...process.env }
delete env.ELECTRON_RUN_AS_NODE

const child = spawn('vite', [], {
  stdio: 'inherit',
  env,
  shell: true,
})
child.on('exit', (code) => process.exit(code ?? 0))
