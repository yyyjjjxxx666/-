<template>
  <div>
    <div class="page-header">
      <h2>🤖 AI智能服务</h2>
      <el-tag>Powered by DeepSeek</el-tag>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="🎯 智能推荐" name="recommend">
        <el-card class="card">
          <el-form :inline="true">
            <el-form-item label="您的兴趣">
              <el-input v-model="interests" placeholder="如：篮球,编程,摄影" style="width:300px" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" @click="handleRecommend">智能推荐</el-button>
            </el-form-item>
          </el-form>

          <div v-if="results.length" class="results">
            <el-card v-for="(item, i) in results" :key="item.club_id" class="result-card" shadow="hover">
              <div class="rank">#{{ i + 1 }}</div>
              <div class="info">
                <h3>{{ item.club_name || '社团 #' + item.club_id }}</h3>
                <el-tag v-if="item.category" size="small" :type="categoryTagType(item.category)" style="margin-bottom:4px">{{ item.category }}</el-tag>
                <p class="reason">{{ item.reason }}</p>
                <div v-if="item.highlights && item.highlights.length" class="highlights">
                  <el-tag v-for="h in item.highlights" :key="h" size="small" effect="plain" style="margin-right:4px">✨ {{ h }}</el-tag>
                </div>
              </div>
              <div class="rec-feedback">
                <el-button size="small" :type="item._fb === 'liked' ? 'primary' : 'default'" circle @click.stop="handleRecFeedback(item, 'liked')">👍</el-button>
                <el-button size="small" :type="item._fb === 'disliked' ? 'danger' : 'default'" circle @click.stop="handleRecFeedback(item, 'disliked')">👎</el-button>
              </div>
            </el-card>
          </div>
          <el-empty v-if="!loading && !results.length && searched" description="暂无推荐结果" />
        </el-card>

        <el-card class="card" style="margin-top:16px">
          <h3 style="margin-bottom:12px">📝 AI文案生成</h3>
          <el-input v-model="copyPrompt" type="textarea" :rows="3" placeholder="描述您要生成的文案需求..." />
          <el-button type="success" :loading="copyLoading" @click="handleCopy" style="margin-top:12px">生成文案</el-button>
          <div v-if="generatedCopy" class="copy-result">{{ generatedCopy }}</div>
        </el-card>
      </el-tab-pane>

      <!-- Knowledge Base Tab -->
      <el-tab-pane label="📚 AI知识问答" name="knowledge">
        <el-row :gutter="16">
          <el-col :span="14">
            <el-card class="card">
              <h3 style="margin-bottom:12px">💬 向知识库提问</h3>
              <el-input v-model="kbQuestion" placeholder="输入问题，如：社团成立需要什么条件？" @keyup.enter="handleAsk" />
              <el-button type="primary" :loading="kbAsking" @click="handleAsk" style="margin-top:12px">提问</el-button>
              <div v-if="kbAnswer" class="kb-answer">
                <div class="answer-label">📖 回答：</div>
                <div class="answer-text">{{ kbAnswer }}</div>
                <div v-if="kbSources.length" class="answer-sources">
                  参考来源：<el-tag v-for="s in kbSources" :key="s" size="small" style="margin-right:4px">{{ s }}</el-tag>
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="10">
            <el-card class="card">
              <template #header>
                <div style="display:flex;justify-content:space-between;align-items:center">
                  <span>📄 知识库文档</span>
                  <el-button v-if="canUpload" size="small" type="primary" @click="uploadVisible = true">上传文档</el-button>
                </div>
              </template>
              <div v-if="kbDocs.length">
                <div v-for="doc in kbDocs" :key="doc.doc_id" class="kb-doc-item">
                  <div>
                    <strong>{{ doc.title }}</strong>
                    <el-tag size="small" style="margin-left:8px">{{ doc.category }}</el-tag>
                    <span style="color:#999;font-size:12px;margin-left:8px">{{ doc.chunks }} 块</span>
                  </div>
                  <el-button v-if="canUpload" size="small" type="danger" text @click="handleDeleteDoc(doc.doc_id)">删除</el-button>
                </div>
              </div>
              <el-empty v-else description="暂无文档" :image-size="60" />
              <div style="margin-top:12px;color:#999;font-size:12px">
                文档数：{{ kbStatsData.documents || 0 }} | 片段数：{{ kbStatsData.chunks || 0 }}
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>
    </el-tabs>

    <!-- Upload Document Dialog -->
    <el-dialog v-model="uploadVisible" title="上传知识库文档" width="500px">
      <el-form :model="uploadForm">
        <el-form-item label="标题">
          <el-input v-model="uploadForm.title" placeholder="文档标题" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="uploadForm.category" style="width:100%">
            <el-option label="社团章程" value="章程" />
            <el-option label="规章制度" value="制度" />
            <el-option label="活动总结" value="总结" />
            <el-option label="通用" value="general" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="uploadForm.content" type="textarea" :rows="8" placeholder="粘贴文档内容..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { aiRecommend, aiRecommendFeedback, aiGenerateCopy, kbAddDoc, kbQuery, kbDeleteDoc, kbListDocs, kbStats, kbAsk } from '../api'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const activeTab = ref('recommend')

const canUpload = computed(() => userStore.role === 'admin' || userStore.role === 'president')

// ── Recommend ──
const interests = ref('')
const loading = ref(false)
const results = ref([])
const searched = ref(false)
const copyPrompt = ref('')
const copyLoading = ref(false)
const generatedCopy = ref('')

const handleRecommend = async () => {
  loading.value = true; searched.value = true
  try {
    const { data } = await aiRecommend({ user_id: userStore.userInfo.id, top_k: 5 })
    if (data.recommendations) results.value = data.recommendations.slice(0, 5)
  } catch {} finally { loading.value = false }
}

const handleCopy = async () => {
  if (!copyPrompt.value) return ElMessage.warning('请输入文案需求')
  copyLoading.value = true
  try {
    const { data } = await aiGenerateCopy({ prompt: copyPrompt.value })
    generatedCopy.value = data.text
  } catch {} finally { copyLoading.value = false }
}

const categoryTagType = (cat) => {
  const map = { '兴趣匹配': 'success', '热门推荐': 'warning', '探索新领域': 'info', '高评分推荐': '', '基于你的活动偏好': 'primary', '综合推荐': 'info' }
  return map[cat] || 'info'
}

const handleRecFeedback = async (item, type) => {
  if (item._fb === type) { item._fb = null; return }
  item._fb = type
  try {
    await aiRecommendFeedback({ user_id: userStore.userInfo.id, club_id: item.club_id, feedback: type === 'liked' ? 'liked' : 'disliked' })
  } catch {}
}

// ── Knowledge Base ──
const kbQuestion = ref('')
const kbAsking = ref(false)
const kbAnswer = ref('')
const kbSources = ref([])
const kbDocs = ref([])
const kbStatsData = reactive({ documents: 0, chunks: 0 })
const uploadVisible = ref(false)
const uploading = ref(false)
const uploadForm = reactive({ title: '', content: '', category: 'general' })

const handleAsk = async () => {
  if (!kbQuestion.value.trim()) return ElMessage.warning('请输入问题')
  kbAsking.value = true
  try {
    const { data } = await kbAsk({ question: kbQuestion.value })
    kbAnswer.value = data.answer
    kbSources.value = data.sources || []
  } catch {} finally { kbAsking.value = false }
}

const fetchKBDocs = async () => {
  try {
    const [docsRes, statsRes] = await Promise.all([kbListDocs(), kbStats()])
    kbDocs.value = docsRes.data.documents || []
    Object.assign(kbStatsData, statsRes.data)
  } catch {}
}

const handleUpload = async () => {
  if (!uploadForm.title || !uploadForm.content) { ElMessage.warning('请填写标题和内容'); return }
  uploading.value = true
  try {
    await kbAddDoc({ title: uploadForm.title, content: uploadForm.content, category: uploadForm.category })
    ElMessage.success('上传成功')
    uploadVisible.value = false
    uploadForm.title = ''; uploadForm.content = ''; uploadForm.category = 'general'
    fetchKBDocs()
  } catch {} finally { uploading.value = false }
}

const handleDeleteDoc = async (id) => {
  try {
    await kbDeleteDoc(id)
    ElMessage.success('已删除')
    fetchKBDocs()
  } catch {}
}

onMounted(fetchKBDocs)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.card { padding: 8px; }
.results { margin-top: 16px; display: flex; flex-direction: column; gap: 12px; }
.result-card { display: flex; gap: 16px; align-items: center; }
.rank { font-size: 24px; font-weight: bold; color: #1e3c72; min-width: 40px; }
.info h3 { margin: 0 0 4px; }
.reason { color: #666; font-size: 14px; margin: 4px 0; }
.highlights { margin-top: 6px; }
.rec-feedback { margin-left: auto; display: flex; gap: 4px; align-items: center; }
.rec-feedback .el-button { margin-left: 0; }
.copy-result { margin-top: 12px; padding: 16px; background: #f5f5f5; border-radius: 8px; white-space: pre-wrap; }
.kb-answer { margin-top: 12px; padding: 16px; background: #f0f7ff; border-radius: 8px; }
.answer-label { font-weight: bold; margin-bottom: 8px; }
.answer-text { line-height: 1.6; margin-bottom: 8px; }
.answer-sources { color: #999; font-size: 13px; }
.kb-doc-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
</style>
