<template>
  <div class="ai-assistant">
    <!-- Collapsed Bubble -->
    <div v-if="!expanded" class="ai-bubble" @click="expanded = true">
      <div class="bubble-ring" />
      <div class="bubble-inner">
        <el-icon :size="26"><Cpu /></el-icon>
      </div>
    </div>

    <!-- Expanded Chat Window -->
    <transition name="scale">
      <div v-if="expanded" class="ai-chat-window">
        <!-- Header -->
        <div class="chat-header">
          <div class="chat-header-left">
            <div class="chat-avatar">
              <el-icon :size="18"><Cpu /></el-icon>
            </div>
            <div>
              <div class="chat-title">AI 小助手</div>
              <div class="chat-subtitle">Powered by DeepSeek</div>
            </div>
          </div>
          <el-button size="small" text class="close-btn" @click="expanded = false">
            <el-icon :size="18"><Close /></el-icon>
          </el-button>
        </div>

        <!-- Quick Actions -->
        <div class="quick-actions">
          <el-button v-for="qa in quickActions" :key="qa" size="small" round class="qa-btn" @click="sendMessage(qa)" :disabled="streaming">
            {{ qa }}
          </el-button>
        </div>

        <!-- Messages -->
        <div class="chat-messages" ref="msgContainer">
          <div v-if="messages.length === 0" class="welcome-msg">
            <el-icon :size="40"><ChatDotRound /></el-icon>
            <p>你好！我是社团管理系统的 AI 小助手。</p>
            <p>你可以问我关于社团、活动、系统使用的任何问题～</p>
          </div>
          <div v-for="(msg, i) in messages" :key="i" :class="['msg', msg.role === 'user' ? 'msg-user' : 'msg-ai']">
            <div class="msg-content">{{ msg.content }}</div>
            <div v-if="msg.role === 'ai' && msg.finished" class="msg-feedback">
              <el-button size="small" text @click="handleFeedback(msg, 'like')">
                <el-icon :size="14"><Star /></el-icon>
              </el-button>
              <el-button size="small" text @click="handleFeedback(msg, 'dislike')">
                <el-icon :size="14"><CloseBold /></el-icon>
              </el-button>
            </div>
          </div>
          <div v-if="streaming" class="msg msg-ai typing-msg">
            <span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>
          </div>
        </div>

        <!-- Input -->
        <div class="chat-input">
          <el-input
            v-model="inputText"
            placeholder="输入你的问题..."
            @keyup.enter="sendMessage(inputText)"
            :disabled="streaming"
            size="large"
            class="msg-input"
          >
            <template #append>
              <el-button type="primary" @click="sendMessage(inputText)" :disabled="streaming || !inputText.trim()" :icon="Promotion">
                发送
              </el-button>
            </template>
          </el-input>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, nextTick, onBeforeUnmount } from 'vue'
import { Promotion } from '@element-plus/icons-vue'

const expanded = ref(false); const inputText = ref(''); const messages = ref([])
const streaming = ref(false); const msgContainer = ref(null); let abortController = null

const quickActions = ['推荐社团', '近期有什么活动', '怎么加入社团', '怎么报名活动']

const sendMessage = async (text) => {
  if (!text || !text.trim() || streaming.value) return
  const trimmed = text.trim()
  messages.value.push({ role: 'user', content: trimmed }); inputText.value = ''; await scrollToBottom()

  streaming.value = true
  const aiMsg = { role: 'ai', content: '', finished: false }
  messages.value.push(aiMsg)

  const token = localStorage.getItem('token') || ''
  abortController = new AbortController()

  try {
    const response = await fetch(`/api/ai/assistant/chat?q=${encodeURIComponent(trimmed)}`, { headers: { 'Authorization': `Bearer ${token}` }, signal: abortController.signal })
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = ''
    while (true) {
      const { done, value } = await reader.read(); if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n'); buffer = ''
      for (const line of lines) {
        if (line.startsWith('data: ')) { const data = line.slice(6); if (data === '[DONE]') continue; aiMsg.content += data } else if (line !== '') { buffer += line + '\n' }
      }
      await scrollToBottom()
    }
  } catch (e) { if (e.name !== 'AbortError') { aiMsg.content += '\n[网络错误，请稍后重试]' } }
  finally { aiMsg.finished = true; streaming.value = false; abortController = null; await scrollToBottom() }
}

const scrollToBottom = async () => { await nextTick(); if (msgContainer.value) msgContainer.value.scrollTop = msgContainer.value.scrollHeight }
const handleFeedback = (msg, type) => { msg._feedback = type }

onBeforeUnmount(() => { if (abortController) abortController.abort() })
</script>

<style scoped>
.ai-assistant { position: fixed; bottom: 28px; right: 28px; z-index: var(--z-fab); }

/* ── Bubble ── */
.ai-bubble {
  width: 60px; height: 60px; border-radius: 50%; cursor: pointer;
  position: relative; display: flex; align-items: center; justify-content: center;
  transition: transform var(--transition-spring), box-shadow var(--transition-base);
}
.ai-bubble:hover { transform: scale(1.08); }
.bubble-ring {
  position: absolute; inset: -3px; border-radius: 50%;
  background: conic-gradient(from 0deg, #7C3AED, #A78BFA, #F97316, #7C3AED);
  animation: spin 3s linear infinite;
  mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 calc(100% - 2px));
  -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 calc(100% - 2px));
}
@keyframes spin { to { transform: rotate(360deg); } }
.bubble-inner {
  width: 54px; height: 54px; border-radius: 50%;
  background: var(--gradient-primary); color: #fff;
  display: flex; align-items: center; justify-content: center;
  position: relative; z-index: 1;
  box-shadow: 0 4px 20px rgba(124, 58, 237, 0.4);
}

/* ── Chat Window ── */
.ai-chat-window {
  width: 400px; height: 560px; border-radius: var(--radius-xl);
  display: flex; flex-direction: column; overflow: hidden;
  position: absolute; bottom: 0; right: 0;
}
.glass-modal { /* using the class from glassmorphism.css */ }
.ai-chat-window {
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: var(--shadow-2xl);
}

/* Header */
.chat-header {
  padding: 14px 16px; display: flex; align-items: center; justify-content: space-between;
  background: var(--gradient-primary); color: #fff;
}
.chat-header-left { display: flex; align-items: center; gap: 10px; }
.chat-avatar {
  width: 36px; height: 36px; border-radius: var(--radius-md);
  background: rgba(255,255,255,0.25); display: flex; align-items: center; justify-content: center;
}
.chat-title { font-size: var(--text-sm); font-weight: var(--font-semibold); }
.chat-subtitle { font-size: 10px; opacity: 0.7; }
.close-btn { color: #fff !important; }

/* Quick Actions */
.quick-actions { padding: 10px 12px; display: flex; flex-wrap: wrap; gap: 6px; border-bottom: 1px solid var(--border-light); }
.qa-btn { border: 1px solid var(--border-light) !important; background: var(--bg-card) !important; color: var(--text-secondary) !important; font-size: var(--text-xs); transition: all var(--transition-fast); }
.qa-btn:hover { border-color: var(--border-accent) !important; color: var(--color-primary-500) !important; }

/* Messages */
.chat-messages {
  flex: 1; padding: 14px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px;
  background: var(--bg-secondary);
}
.welcome-msg { text-align: center; color: var(--text-muted); font-size: var(--text-sm); margin-top: 60px; line-height: 1.8; }
.welcome-msg .el-icon { margin-bottom: 8px; }

.msg { max-width: 85%; padding: 10px 14px; border-radius: var(--radius-md); font-size: var(--text-sm); line-height: 1.6; word-break: break-word; }
.msg-user {
  align-self: flex-end; background: var(--gradient-primary); color: #fff;
  border-bottom-right-radius: 6px;
}
.msg-ai {
  align-self: flex-start;
  background: var(--bg-card); border: 1px solid var(--border-light);
  border-bottom-left-radius: 6px; color: var(--text-primary);
}
.msg-content { white-space: pre-wrap; }
.msg-feedback { margin-top: 4px; display: flex; gap: 2px; justify-content: flex-end; }

.typing-msg { padding: 12px 14px; }
.typing-dots span { display: inline-block; animation: blink-dot 1.4s infinite both; font-size: 20px; line-height: 1; color: var(--text-muted); }
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink-dot { 0%, 80%, 100% { opacity: 0.2; } 40% { opacity: 1; } }

/* Input */
.chat-input { padding: 12px; border-top: 1px solid var(--border-light); }
.msg-input :deep(.el-input-group__append) { padding: 0 4px; background: transparent; }

/* Dark Mode */
[data-theme="dark"] .ai-chat-window {
  background: rgba(30, 41, 59, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.12);
}
[data-theme="dark"] .msg-ai { background: rgba(30, 41, 59, 0.8); }

/* Scale transition */
.scale-enter-active { transition: all var(--transition-spring); }
.scale-leave-active { transition: all var(--transition-fast); }
.scale-enter-from { opacity: 0; transform: scale(0.9) translateY(10px); }
.scale-leave-to { opacity: 0; transform: scale(0.9) translateY(10px); }
</style>
