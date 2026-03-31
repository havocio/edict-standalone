export interface Task {
  id: string
  title: string
  content?: string
  state: string
  created_at: string
  updated_at: string
  result?: string
  flow_log?: FlowLogEntry[]
  progress_log?: ProgressLogEntry[]
}

export interface FlowLogEntry {
  time: string
  from: string
  to: string
  agent: string
  note: string
}

export interface ProgressLogEntry {
  time: string
  agent: string
  doing: string
  todos?: string[]
  tokens?: number
}

export interface TaskStats {
  total: number
  running: number
  done: number
  by_state?: Record<string, number>
}

export interface RegimeInfo {
  id: string
  name: string
  description: string
}
