<template>
  <div class="ai-assistant">
    <!-- Collapsed bubble -->
    <div v-if="!expanded" class="ai-bubble" @click="expanded = true">
      <span class="bubble-icon">🤖</span>
    </div>

    <!-- Expanded chat window -->
    <div v-else class="ai-chat-window">
      <div class="chat-header">
        <span>🤖 AI 小助手</span>
        <span class="chat-header-sub">Powered by DeepSeek</span>
        <el-button size="small" text class="close-btn" @click="expanded = false">✕</el-button>
      </div>

      <!-- Quick actions -->
      <div class="quick-actions">
        <el-button
          v-for="qa in quickActions"
          :key="qa"
          size="small"
          round
          @click="sendMessage(qa)"
          :disabled="streaming"
        >{{ qa }}</el-button>
      </div>

      <!-- Messages area -->
      <div class="chat-messages" ref="msgContainer">
        <div v-if="messages.length === 0" class="welcome-msg">
          <p>👋 你好！我是社团管理系统的 AI 小助手。</p>
          <p>你可以问我关于社团、活动、系统使用的任何问题～</p>
        </div>
        <div
          v-for="(msg, i) in messages"
          :key="i"
          :class="['msg', msg.role === 'user' ? 'msg-user' : 'msg-ai']"
        >
          <div class="msg-content">{{ msg.content }}</div>
          <div v-if="msg.role === 'ai' && msg.finished" class="msg-feedback">
            <el-button size="small" text @click="handleFeedback(msg, 'like')">👍</el-button>
            <el-button size="small" text @click="handleFeedback(msg, 'dislike')">👎</el-button>
          </div>
        </div>
        <div v-if="streaming" class="msg msg-ai typing-msg">
          <span class="typing-cursor">|</span>
        </div>
      </div>

      <!-- Input area -->
      <div class="chat-input">
        <el-input
          v-model="inputText"
          placeholder="输入你的问题..."
          @keyup.enter="sendMessage(inputText)"
          :disabled="streaming"
          clearable
        >
          <template #append>
            <el-button @click="sendMessage(inputText)" :disabled="streaming || !inputText.trim()">
              发送
            </el-button>
          </template>
        </el-input>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onBeforeUnmount } from 'vue'

const expanded = ref(false)
const inputText = ref('')
const messages = ref([])
const streaming = ref(false)
const msgContainer = ref(null)

let abortController = null

const quickActions = [
  '推荐社团',
  '近期有什么活动',
  '怎么加入社团',
  '怎么报名活动',
]

const sendMessage = async (text) => {
  if (!text || !text.trim() || streaming.value) return
  const trimmed = text.trim()
  messages.value.push({ role: 'user', content: trimmed })
  inputText.value = ''
  await scrollToBottom()

  streaming.value = true
  const aiMsg = { role: 'ai', content: '', finished: false }
  messages.value.push(aiMsg)

  const token = localStorage.getItem('token') || ''
  abortController = new AbortController()

  try {
    const response = await fetch(`/api/ai/assistant/chat?q=${encodeURIComponent(trimmed)}`, {
      headers: { 'Authorization': `Bearer ${token}` },
      signal: abortController.signal,
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // Parse SSE data lines
      const lines = buffer.split('\n')
      buffer = ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') continue
          aiMsg.content += data
        } else if (line !== '') {
          // Incomplete line, put back in buffer
          buffer += line + '\n'
        }
      }
      await scrollToBottom()
    }
  } catch (e) {
    if (e.name !== 'AbortError') {
      aiMsg.content += '\n[网络错误，请稍后重试]'
    }
  } finally {
    aiMsg.finished = true
    streaming.value = false
    abortController = null
    await scrollToBottom()
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
}

const handleFeedback = (msg, type) => {
  msg._feedback = type
}

onBeforeUnmount(() => {
  if (abortController) abortController.abort()
})
</script>

<style scoped>
.ai-assistant {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
}

.ai-bubble {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(30, 60, 114, 0.35);
  transition: transform 0.2s, box-shadow 0.2s;
  animation: pulse 2s infinite;
}

.ai-bubble:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 24px rgba(30, 60, 114, 0.5);
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 4px 16px rgba(30, 60, 114, 0.35); }
  50% { box-shadow: 0 4px 24px rgba(30, 60, 114, 0.55); }
}

.bubble-icon {
  font-size: 26px;
}

.ai-chat-window {
  width: 380px;
  height: 520px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-header {
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  color: #fff;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
}

.chat-header-sub {
  font-size: 11px;
  font-weight: 400;
  opacity: 0.7;
  margin-left: auto;
  margin-right: 8px;
}

.close-btn {
  color: #fff !important;
  font-size: 16px;
}

.quick-actions {
  padding: 10px 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  border-bottom: 1px solid #f0f0f0;
}

.chat-messages {
  flex: 1;
  padding: 12px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: #f8f9fb;
}

.welcome-msg {
  text-align: center;
  color: #999;
  font-size: 13px;
  margin-top: 40px;
  line-height: 1.8;
}

.msg {
  max-width: 85%;
  padding: 8px 12px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;
}

.msg-user {
  align-self: flex-end;
  background: #1e3c72;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.msg-ai {
  align-self: flex-start;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-bottom-left-radius: 4px;
}

.msg-content {
  white-space: pre-wrap;
}

.msg-feedback {
  margin-top: 4px;
  display: flex;
  gap: 2px;
  justify-content: flex-end;
}

.typing-msg {
  padding: 8px 12px;
}

.typing-cursor {
  animation: blink 1s infinite;
  color: #1e3c72;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.chat-input {
  padding: 10px 12px;
  border-top: 1px solid #f0f0f0;
}

.chat-input :deep(.el-input-group__append) {
  padding: 0 8px;
}
</style>
