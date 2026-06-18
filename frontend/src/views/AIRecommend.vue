<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">
        <el-icon :size="22"><Cpu /></el-icon>
        AI 智能服务
      </h2>
      <el-tag effect="plain" round>Powered by DeepSeek</el-tag>
    </div>

    <el-tabs v-model="activeTab" class="modern-tabs">
      <!-- Recommend Tab -->
      <el-tab-pane name="recommend">
        <template #label>
          <span class="tab-label"><el-icon :size="16"><Aim /></el-icon> 智能推荐</span>
        </template>

        <div class="glass-card rec-panel" style="cursor:default">
          <div class="section-title">
            <el-icon :size="18"><Search /></el-icon>
            <span>发现适合你的社团</span>
          </div>
          <el-button type="primary" size="large" :loading="loading" @click="handleRecommend" class="rec-btn">
            <el-icon :size="18"><Aim /></el-icon>
            智能推荐
          </el-button>

          <div v-if="results.length" class="results">
            <div v-for="(item, i) in results" :key="item.club_id" class="result-card glass-card" @click="$router.push(`/clubs/${item.club_id}`)">
              <div class="rank-badge" :class="'rank-' + (i + 1)">#{{ i + 1 }}</div>
              <div class="result-info">
                <h3>{{ item.club_name || '社团 #' + item.club_id }}</h3>
                <el-tag v-if="item.category" size="small" :type="categoryTagType(item.category)" round style="margin-bottom:6px">{{ item.category }}</el-tag>
                <p class="reason">{{ item.reason }}</p>
                <div v-if="item.highlights && item.highlights.length" class="highlights">
                  <el-tag v-for="h in item.highlights" :key="h" size="small" effect="plain" round class="hl-tag">
                    <el-icon :size="12"><StarFilled /></el-icon> {{ h }}
                  </el-tag>
                </div>
              </div>
              <div class="rec-feedback" @click.stop>
                <el-button size="small" text :type="item._fb === 'liked' ? 'primary' : ''" @click="handleRecFeedback(item, 'liked')">
                  <el-icon :size="18"><StarFilled /></el-icon>
                </el-button>
                <el-button size="small" text :type="item._fb === 'disliked' ? 'danger' : ''" @click="handleRecFeedback(item, 'disliked')">
                  <el-icon :size="18"><CloseBold /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
          <el-empty v-if="!loading && !results.length && searched" description="暂无推荐结果" />
        </div>

        <div class="glass-card copy-panel" style="margin-top:16px;cursor:default">
          <div class="section-title">
            <el-icon :size="18"><EditPen /></el-icon>
            <span>AI 文案生成</span>
          </div>
          <el-input v-model="copyPrompt" type="textarea" :rows="3" placeholder="描述您要生成的文案需求..." size="large" />
          <el-button type="success" size="large" :loading="copyLoading" @click="handleCopy" style="margin-top:12px">
            <el-icon :size="16"><MagicStick /></el-icon>
            生成文案
          </el-button>
          <div v-if="generatedCopy" class="copy-result">{{ generatedCopy }}</div>
        </div>
      </el-tab-pane>

      <!-- Knowledge Base Tab (Admin Only) -->
      <el-tab-pane v-if="isAdmin" name="knowledge">
        <template #label>
          <span class="tab-label"><el-icon :size="16"><Reading /></el-icon> 相关文档上传</span>
        </template>

            <div class="glass-card kb-docs" style="cursor:default">
              <div class="section-title">
                <el-icon :size="18"><Document /></el-icon>
                <span>知识库文档</span>
                <el-button v-if="canUpload" size="small" type="primary" @click="uploadVisible = true" style="margin-left:auto">
                  <el-icon :size="14"><Plus /></el-icon> 上传
                </el-button>
              </div>
              <div v-if="kbDocs.length" class="doc-list">
                <div v-for="doc in kbDocs" :key="doc.doc_id" class="doc-item">
                  <div class="doc-info">
                    <strong>{{ doc.title }}</strong>
                    <div class="doc-meta">
                      <el-tag size="small" round>{{ doc.category }}</el-tag>
                      <span class="chunks-count">{{ doc.chunks }} 块</span>
                    </div>
                  </div>
                  <el-button v-if="canUpload" size="small" type="danger" text @click="handleDeleteDoc(doc.doc_id)">
                    <el-icon :size="14"><Delete /></el-icon>
                  </el-button>
                </div>
              </div>
              <el-empty v-else description="暂无文档" :image-size="60" />
              <div class="kb-stats">
                <span><el-icon :size="14"><Document /></el-icon> 文档：{{ kbStatsData.documents || 0 }}</span>
                <span><el-icon :size="14"><Collection /></el-icon> 片段：{{ kbStatsData.chunks || 0 }}</span>
              </div>
            </div>
      </el-tab-pane>
    </el-tabs>

    <!-- Upload Document Dialog -->
    <el-dialog v-model="uploadVisible" title="上传知识库文档" width="500px" class="modern-dialog">
      <el-form :model="uploadForm" label-position="top">
        <el-form-item label="选择文档">
          <div class="file-upload-area" @click="fileInputRef?.click()" @dragover.prevent @drop.prevent="onFileDrop">
            <input ref="fileInputRef" type="file" accept=".docx,.doc,.md,.txt,.pdf" style="display:none" @change="onFileSelected" />
            <template v-if="!selectedFile">
              <el-icon :size="40"><UploadFilled /></el-icon>
              <p class="upload-hint">点击选择文档或拖拽到此处</p>
              <p class="upload-formats">支持 .docx .doc .md .txt .pdf</p>
            </template>
            <template v-else>
              <div class="file-selected">
                <el-icon :size="32"><Document /></el-icon>
                <div class="file-info">
                  <strong>{{ selectedFile.name }}</strong>
                  <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
                </div>
                <el-button size="small" type="danger" text @click.stop="clearFile">移除</el-button>
              </div>
            </template>
          </div>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="uploadForm.title" placeholder="文档标题" size="large" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="uploadForm.category" style="width:100%" size="large">
            <el-option label="社团章程" value="章程" />
            <el-option label="规章制度" value="制度" />
            <el-option label="活动总结" value="总结" />
            <el-option label="通用" value="general" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" :disabled="!selectedFile" @click="handleUpload">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { aiRecommend, aiRecommendFeedback, aiGenerateCopy, kbAddDoc, kbUploadDoc, kbDeleteDoc, kbListDocs, kbStats } from '../api'
import { useUserStore } from '../stores/user'

const userStore = useUserStore(); const activeTab = ref('recommend')
const isAdmin = computed(() => userStore.role === 'admin')
const canUpload = computed(() => userStore.role === 'admin')

const interests = ref(''); const loading = ref(false); const results = ref([]); const searched = ref(false)
const copyPrompt = ref(''); const copyLoading = ref(false); const generatedCopy = ref('')

const handleRecommend = async () => {
  loading.value = true; searched.value = true
  try { const { data } = await aiRecommend({ user_id: userStore.userInfo.id, top_k: 5 }); if (data.recommendations) results.value = data.recommendations.slice(0, 5) } catch {} finally { loading.value = false }
}
const handleCopy = async () => {
  if (!copyPrompt.value) return ElMessage.warning('请输入文案需求')
  copyLoading.value = true
  try { const { data } = await aiGenerateCopy({ prompt: copyPrompt.value }); generatedCopy.value = data.text } catch {} finally { copyLoading.value = false }
}
const categoryTagType = (cat) => {
  const map = { '兴趣匹配': 'success', '热门推荐': 'warning', '探索新领域': 'info', '高评分推荐': '', '基于你的活动偏好': 'primary', '综合推荐': 'info' }
  return map[cat] || 'info'
}
const handleRecFeedback = async (item, type) => {
  if (item._fb === type) { item._fb = null; return }
  item._fb = type
  try { await aiRecommendFeedback({ user_id: userStore.userInfo.id, club_id: item.club_id, feedback: type === 'liked' ? 'liked' : 'disliked' }) } catch {}
}

const kbDocs = ref([]); const kbStatsData = reactive({ documents: 0, chunks: 0 })
const uploadVisible = ref(false); const uploading = ref(false)
const uploadForm = reactive({ title: '', category: 'general' })
const selectedFile = ref(null)
const fileInputRef = ref(null)

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
const onFileSelected = (e) => {
  const file = e.target.files?.[0]; if (!file) return
  selectedFile.value = file
  // Auto-fill title from filename (remove extension)
  const name = file.name.replace(/\.[^.]+$/, '')
  if (!uploadForm.title) uploadForm.title = name
}
const onFileDrop = (e) => {
  const file = e.dataTransfer?.files?.[0]; if (!file) return
  const ext = file.name.split('.').pop()?.toLowerCase()
  const allowed = ['docx', 'doc', 'md', 'txt', 'pdf']
  if (!allowed.includes(ext)) { ElMessage.warning(`不支持的文件格式: .${ext}`); return }
  selectedFile.value = file
  if (!uploadForm.title) uploadForm.title = file.name.replace(/\.[^.]+$/, '')
}
const clearFile = () => { selectedFile.value = null; if (fileInputRef.value) fileInputRef.value.value = '' }

const fetchKBDocs = async () => {
  try { const [docsRes, statsRes] = await Promise.all([kbListDocs(), kbStats()]); kbDocs.value = docsRes.data.documents || []; Object.assign(kbStatsData, statsRes.data) } catch {}
}
const handleUpload = async () => {
  if (!selectedFile.value) { ElMessage.warning('请选择文档文件'); return }
  if (!uploadForm.title) { ElMessage.warning('请填写文档标题'); return }
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', selectedFile.value)
    fd.append('title', uploadForm.title)
    fd.append('category', uploadForm.category)
    await kbUploadDoc(fd)
    ElMessage.success('上传成功')
    uploadVisible.value = false
    uploadForm.title = ''
    uploadForm.category = 'general'
    selectedFile.value = null
    if (fileInputRef.value) fileInputRef.value.value = ''
    fetchKBDocs()
  } catch {} finally { uploading.value = false }
}
const handleDeleteDoc = async (id) => { try { await kbDeleteDoc(id); ElMessage.success('已删除'); fetchKBDocs() } catch {} }

onMounted(() => { if (isAdmin.value) fetchKBDocs() })
</script>

<style scoped>
.page-container { max-width: 1200px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-title { display: flex; align-items: center; gap: 10px; font-size: var(--text-2xl); font-weight: var(--font-bold); color: var(--text-primary); margin: 0; }
.tab-label { display: flex; align-items: center; gap: 6px; }

/* Modern Tabs */
.modern-tabs :deep(.el-tabs__active-bar) { background: var(--gradient-primary) !important; height: 3px !important; border-radius: var(--radius-full); }
.modern-tabs :deep(.el-tabs__item) { font-size: var(--text-sm); color: var(--text-muted); }
.modern-tabs :deep(.el-tabs__item):hover { color: var(--color-primary-500); }
.modern-tabs :deep(.el-tabs__item.is-active) { color: var(--color-primary-600); font-weight: var(--font-semibold); }
.modern-tabs :deep(.el-tabs__nav-wrap::after) { background: var(--border-light); }

.rec-panel, .copy-panel, .kb-chat, .kb-docs { padding: 24px; }
.section-title { display: flex; align-items: center; gap: 8px; font-size: var(--text-base); font-weight: var(--font-semibold); color: var(--text-primary); margin-bottom: 16px; }
.rec-btn { margin-bottom: 16px; }

/* Results */
.results { display: flex; flex-direction: column; gap: 12px; margin-top: 16px; }
.result-card { display: flex; gap: 16px; align-items: center; padding: 16px; }
.rank-badge { font-size: var(--text-2xl); font-weight: var(--font-bold); min-width: 48px; text-align: center; }
.rank-1 { color: #F59E0B; }
.rank-2 { color: #94A3B8; }
.rank-3 { color: #D97706; }
.result-info { flex: 1; }
.result-info h3 { margin: 0 0 4px; font-size: var(--text-base); color: var(--text-primary); }
.reason { color: var(--text-secondary); font-size: var(--text-sm); margin: 4px 0; }
.highlights { margin-top: 6px; display: flex; gap: 4px; flex-wrap: wrap; }
.hl-tag { margin-right: 0; }
.rec-feedback { display: flex; gap: 4px; flex-shrink: 0; }

.copy-result { margin-top: 12px; padding: 20px; background: var(--bg-secondary); border-radius: var(--radius-md); white-space: pre-wrap; color: var(--text-primary); line-height: 1.7; }

/* KB */
.kb-answer { padding: 20px; margin-top: 16px; }
.answer-label { font-weight: var(--font-semibold); margin-bottom: 8px; color: var(--text-primary); display: flex; align-items: center; gap: 6px; }
.answer-text { line-height: 1.7; color: var(--text-primary); margin-bottom: 12px; }
.answer-sources { color: var(--text-muted); font-size: var(--text-sm); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.doc-list { display: flex; flex-direction: column; gap: 4px; }
.doc-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--border-light); }
.doc-info strong { display: block; color: var(--text-primary); font-size: var(--text-sm); }
.doc-meta { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.chunks-count { color: var(--text-muted); font-size: var(--text-xs); }
.kb-stats { margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--border-light); color: var(--text-muted); font-size: var(--text-xs); display: flex; justify-content: space-between; }

/* File Upload */
.file-upload-area {
  border: 2px dashed var(--border-accent); border-radius: var(--radius-lg);
  padding: 32px; text-align: center; cursor: pointer;
  transition: border-color var(--transition-fast), background var(--transition-fast);
  background: var(--bg-secondary);
}
.file-upload-area:hover { border-color: var(--color-primary-400); background: var(--gradient-card-accent); }
.upload-hint { color: var(--text-secondary); margin: 8px 0 4px; font-size: var(--text-sm); }
.upload-formats { color: var(--text-muted); font-size: var(--text-xs); margin: 0; }
.file-selected { display: flex; align-items: center; gap: 16px; }
.file-info { text-align: left; flex: 1; }
.file-info strong { display: block; color: var(--text-primary); font-size: var(--text-sm); word-break: break-all; }
.file-size { color: var(--text-muted); font-size: var(--text-xs); }
</style>
