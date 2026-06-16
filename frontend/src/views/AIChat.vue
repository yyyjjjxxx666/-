<template>
  <div class="chat-page">
    <!-- Left Sidebar: Conversation List -->
    <aside class="chat-sidebar glass-card" style="cursor:default">
      <div class="sidebar-header">
        <el-button type="primary" class="new-chat-btn" @click="handleNewChat" :loading="creating">
          <el-icon :size="16"><Plus /></el-icon>
          新建对话
        </el-button>
      </div>
      <div class="conversation-list" v-loading="loadingConvs">
        <div v-if="conversations.length === 0 && !loadingConvs" class="empty-convs">
          暂无对话，点击上方按钮开始
        </div>
        <div
          v-for="conv in conversations"
          :key="conv.id"
          :class="['conv-item', { active: currentConvId === conv.id }]"
          @click="switchConversation(conv.id)"
        >
          <div class="conv-info">
            <div class="conv-title">{{ conv.title }}</div>
            <div class="conv-meta">{{ conv.updated_at?.slice(0, 16) || '' }} · {{ conv.message_count }}条</div>
          </div>
          <el-popconfirm title="确定删除此对话？" confirm-button-text="删除" cancel-button-text="取消" @confirm.stop="handleDeleteConv(conv.id)">
            <template #reference>
              <el-button class="conv-delete" size="small" text @click.stop>
                <el-icon :size="14"><Delete /></el-icon>
              </el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>
    </aside>

    <!-- Right: Chat Area -->
    <main class="chat-main glass-card" style="cursor:default">
      <!-- No conversation selected -->
      <div v-if="!currentConvId" class="chat-welcome">
        <div class="welcome-icon">
          <el-icon :size="64"><ChatDotRound /></el-icon>
        </div>
        <h2>AI 智能助手</h2>
        <p class="welcome-sub">Powered by DeepSeek · 支持多轮对话 · 对话自动保存</p>
        <div class="welcome-tips">
          <p>选择一个已有对话，或创建一个新对话开始聊天</p>
          <div class="quick-prompts">
            <span class="prompt-tag" @click="startNewWithPrompt('帮我推荐适合我的社团')">🎯 推荐社团</span>
            <span class="prompt-tag" @click="startNewWithPrompt('最近有什么新活动？')">📅 近期活动</span>
            <span class="prompt-tag" @click="startNewWithPrompt('怎么加入社团？')">❓ 加入社团</span>
            <span class="prompt-tag" @click="startNewWithPrompt('如何报名活动？')">✍️ 报名活动</span>
          </div>
        </div>
      </div>

      <!-- Active conversation -->
      <template v-else>
        <!-- Chat header -->
        <div class="chat-topbar">
          <div class="conv-title-display">
            <template v-if="editingTitle">
              <el-input
                v-model="editTitleText"
                size="small"
                class="title-input"
                @keyup.enter="saveTitle"
                @blur="saveTitle"
                ref="titleInputRef"
              />
            </template>
            <template v-else>
              <span class="current-title" @dblclick="startEditTitle">{{ currentConvTitle }}</span>
              <el-button size="small" text @click="startEditTitle">
                <el-icon :size="14"><Edit /></el-icon>
              </el-button>
            </template>
          </div>
        </div>

        <!-- Messages -->
        <div class="chat-messages" ref="msgContainer">
          <div v-if="messages.length === 0 && !streaming" class="empty-hint">
            发送消息开始对话
          </div>
          <div
            v-for="(msg, i) in messages"
            :key="i"
            :class="['msg', msg.role === 'user' ? 'msg-user' : 'msg-ai']"
          >
            <div class="msg-avatar">
              <el-icon v-if="msg.role === 'user'" :size="18"><User /></el-icon>
              <el-icon v-else :size="18"><Cpu /></el-icon>
            </div>
            <div class="msg-body">
              <div class="msg-content">{{ msg.content }}</div>
            </div>
          </div>
          <div v-if="streaming" class="msg msg-ai">
            <div class="msg-avatar">
              <el-icon :size="18"><Cpu /></el-icon>
            </div>
            <div class="msg-body">
              <div class="msg-content">
                {{ streamingText }}
                <span class="typing-cursor">|</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Input -->
        <div class="chat-input-area">
          <el-input
            v-model="inputText"
            placeholder="输入你的问题... (Enter 发送)"
            @keyup.enter="sendMessage"
            :disabled="streaming"
            size="large"
            class="msg-input"
          >
            <template #append>
              <el-button
                type="primary"
                @click="sendMessage"
                :disabled="streaming || !inputText.trim()"
                :loading="streaming"
              >
                <el-icon :size="16"><Promotion /></el-icon>
                发送
              </el-button>
            </template>
          </el-input>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getConversations, createConversation, getMessages,
  deleteConversation, updateConversationTitle
} from '../api'

// ── State ──
const conversations = ref([])
const currentConvId = ref(null)
const messages = ref([])
const inputText = ref('')
const streaming = ref(false)
const streamingText = ref('')
const loadingConvs = ref(false)
const creating = ref(false)

const editingTitle = ref(false)
const editTitleText = ref('')
const titleInputRef = ref(null)

const msgContainer = ref(null)
let abortController = null

// ── Computed ──
const currentConvTitle = computed(() => {
  const conv = conversations.value.find(c => c.id === currentConvId.value)
  return conv ? conv.title : '对话'
})

// ── Methods ──
const fetchConversations = async () => {
  loadingConvs.value = true
  try {
    const { data } = await getConversations()
    conversations.value = data || []
  } catch {} finally { loadingConvs.value = false }
}

const handleNewChat = async () => {
  creating.value = true
  try {
    const { data } = await createConversation()
    conversations.value.unshift({ ...data, message_count: 0, updated_at: data.created_at })
    currentConvId.value = data.id
    messages.value = []
    inputText.value = ''
    streamingText.value = ''
  } catch {} finally { creating.value = false }
}

const switchConversation = async (id) => {
  if (id === currentConvId.value) return
  if (streaming.value) {
    if (abortController) abortController.abort()
    streaming.value = false
    streamingText.value = ''
  }
  currentConvId.value = id
  messages.value = []
  inputText.value = ''
  try {
    const { data } = await getMessages(id)
    messages.value = data || []
  } catch {}
  await nextTick()
  scrollToBottom()
}

const handleDeleteConv = async (id) => {
  try {
    await deleteConversation(id)
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (currentConvId.value === id) {
      currentConvId.value = null
      messages.value = []
    }
    ElMessage.success('对话已删除')
  } catch {}
}

const startEditTitle = () => {
  editTitleText.value = currentConvTitle.value
  editingTitle.value = true
  nextTick(() => { if (titleInputRef.value) titleInputRef.value.focus() })
}

const saveTitle = async () => {
  if (!editingTitle.value) return
  editingTitle.value = false
  const newTitle = editTitleText.value.trim()
  if (!newTitle || newTitle === currentConvTitle.value) return
  try {
    await updateConversationTitle(currentConvId.value, newTitle)
    const conv = conversations.value.find(c => c.id === currentConvId.value)
    if (conv) conv.title = newTitle
  } catch {}
}

const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text || streaming.value) return

  // Ensure we have a conversation
  if (!currentConvId.value) {
    await handleNewChat()
  }

  inputText.value = ''
  messages.value.push({ role: 'user', content: text })
  await nextTick()
  scrollToBottom()

  // Start SSE streaming
  streaming.value = true
  streamingText.value = ''
  abortController = new AbortController()

  const token = localStorage.getItem('token') || ''
  try {
    const response = await fetch(`/api/ai/conversations/${currentConvId.value}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ message: text }),
      signal: abortController.signal,
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') continue
          if (data.startsWith('[错误:')) {
            streamingText.value += data
            continue
          }
          streamingText.value += data
        } else if (line !== '') {
          buffer += line + '\n'
        }
      }
      await nextTick()
      scrollToBottom()
    }
  } catch (e) {
    if (e.name !== 'AbortError') {
      streamingText.value += '\n[网络错误，请稍后重试]'
    }
  } finally {
    // Save completed AI message to local state
    if (streamingText.value) {
      messages.value.push({ role: 'assistant', content: streamingText.value })
    }
    streaming.value = false
    streamingText.value = ''
    abortController = null
    await nextTick()
    scrollToBottom()

    // Refresh conversation list to update title/time
    fetchConversations()
  }
}

const startNewWithPrompt = async (prompt) => {
  await handleNewChat()
  inputText.value = prompt
  await nextTick()
  sendMessage()
}

const scrollToBottom = () => {
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
}

// Watch current conversation to refresh message list
watch(currentConvId, () => {})

onBeforeUnmount(() => {
  if (abortController) abortController.abort()
})

// Init
fetchConversations()
</script>

<style scoped>
.chat-page {
  display: flex; height: calc(100vh - 100px); gap: 16px;
  max-width: 1400px; margin: 0 auto;
}

/* ── Sidebar ── */
.chat-sidebar {
  width: 260px; flex-shrink: 0; border-radius: var(--radius-xl);
  background: var(--bg-card); border: 1px solid var(--border-light);
  display: flex; flex-direction: column; overflow: hidden;
}
.sidebar-header { padding: 16px; }
.new-chat-btn { width: 100%; }
.conversation-list { flex: 1; overflow-y: auto; padding: 0 12px 12px; }
.empty-convs { text-align: center; padding: 40px 16px; font-size: var(--text-sm); color: var(--text-muted); }

.conv-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px; border-radius: var(--radius-md); cursor: pointer;
  transition: background var(--transition-fast); margin-bottom: 4px;
}
.conv-item:hover { background: var(--bg-secondary); }
.conv-item.active { background: var(--color-primary-50); }
.conv-item.active .conv-title { color: var(--color-primary-600); font-weight: var(--font-semibold); }
[data-theme="dark"] .conv-item.active { background: rgba(124, 58, 237, 0.12); }
.conv-info { flex: 1; overflow: hidden; }
.conv-title { font-size: var(--text-sm); color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.conv-meta { font-size: var(--text-xs); color: var(--text-muted); margin-top: 2px; }
.conv-delete { opacity: 0; transition: opacity var(--transition-fast); color: var(--text-muted) !important; }
.conv-item:hover .conv-delete { opacity: 1; }

/* ── Main Chat Area ── */
.chat-main {
  flex: 1; display: flex; flex-direction: column; border-radius: var(--radius-xl);
  background: var(--bg-card); border: 1px solid var(--border-light); overflow: hidden;
}

/* Welcome */
.chat-welcome { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px; text-align: center; }
.welcome-icon {
  width: 100px; height: 100px; border-radius: 50%;
  background: var(--gradient-primary); display: flex; align-items: center; justify-content: center;
  color: #fff; margin-bottom: 20px;
  box-shadow: 0 8px 32px rgba(124, 58, 237, 0.25);
}
.chat-welcome h2 { font-size: var(--text-2xl); font-weight: var(--font-bold); color: var(--text-primary); margin: 0 0 6px; }
.welcome-sub { font-size: var(--text-sm); color: var(--text-muted); margin: 0 0 24px; }
.welcome-tips p { font-size: var(--text-sm); color: var(--text-secondary); margin: 0 0 12px; }
.quick-prompts { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }
.prompt-tag {
  display: inline-block; padding: 6px 16px; border-radius: var(--radius-full);
  border: 1px solid var(--border-light); font-size: var(--text-sm);
  color: var(--text-secondary); cursor: pointer;
  transition: all var(--transition-fast); background: var(--bg-secondary);
}
.prompt-tag:hover { border-color: var(--border-accent); color: var(--color-primary-500); background: var(--color-primary-50); }

/* Top bar */
.chat-topbar {
  padding: 12px 20px; border-bottom: 1px solid var(--border-light);
  display: flex; align-items: center;
}
.conv-title-display { display: flex; align-items: center; gap: 8px; }
.current-title { font-size: var(--text-base); font-weight: var(--font-semibold); color: var(--text-primary); }
.title-input { width: 260px; }

/* Messages */
.chat-messages {
  flex: 1; overflow-y: auto; padding: 20px 24px;
  display: flex; flex-direction: column; gap: 16px;
  background: var(--bg-secondary);
}
.empty-hint { text-align: center; color: var(--text-muted); font-size: var(--text-sm); margin-top: 40px; }

.msg { display: flex; gap: 10px; max-width: 80%; }
.msg-user { align-self: flex-end; flex-direction: row-reverse; }
.msg-ai { align-self: flex-start; }

.msg-avatar {
  width: 34px; height: 34px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.msg-user .msg-avatar {
  background: var(--gradient-primary); color: #fff;
}
.msg-ai .msg-avatar {
  background: var(--bg-card); border: 1px solid var(--border-light); color: var(--color-primary-500);
}

.msg-body { flex: 1; min-width: 0; }
.msg-content {
  padding: 10px 16px; border-radius: var(--radius-md); font-size: var(--text-sm);
  line-height: 1.7; white-space: pre-wrap; word-break: break-word;
}
.msg-user .msg-content {
  background: var(--gradient-primary); color: #fff;
  border-bottom-right-radius: 4px;
}
.msg-ai .msg-content {
  background: var(--bg-card); border: 1px solid var(--border-light);
  border-bottom-left-radius: 4px; color: var(--text-primary);
}

.typing-cursor {
  display: inline; animation: blink 1s infinite; font-weight: var(--font-bold);
  color: var(--color-primary-500);
}
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

/* Input */
.chat-input-area { padding: 16px 20px; border-top: 1px solid var(--border-light); }
.msg-input :deep(.el-input-group__append) { padding: 0 4px; background: transparent; }

/* Dark mode */
[data-theme="dark"] .chat-sidebar,
[data-theme="dark"] .chat-main { background: rgba(30, 41, 59, 0.9); border-color: rgba(148, 163, 184, 0.12); }
[data-theme="dark"] .msg-ai .msg-content { background: rgba(30, 41, 59, 0.8); }
[data-theme="dark"] .msg-ai .msg-avatar { background: rgba(30, 41, 59, 0.8); }

/* Responsive */
@media (max-width: 768px) {
  .chat-page { flex-direction: column; height: auto; }
  .chat-sidebar { width: 100%; max-height: 200px; }
  .chat-main { min-height: 500px; }
}
</style>
