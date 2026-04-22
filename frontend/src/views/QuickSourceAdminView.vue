<template>
  <div class="source-admin-page">
    <header class="source-admin-top surface-card">
      <div>
        <span class="section-chip">Quick Source Admin</span>
        <h1>速看来源配置</h1>
        <p>在这里统一维护权威机构入口、创作者平台分组与精选创作者资料，直接服务于“速看辟谣”页面。</p>
      </div>

      <div class="top-actions">
        <button class="ghost-btn" @click="router.push('/quickly_look')">查看速看页</button>
        <button class="ghost-btn" @click="router.push('/admin')">返回管理员台</button>
      </div>
    </header>

    <section class="mini-grid">
      <article class="mini-card surface-card">
        <span>来源平台总数</span>
        <strong>{{ overview.platform_total }}</strong>
      </article>
      <article class="mini-card surface-card">
        <span>权威机构</span>
        <strong>{{ overview.official_total }}</strong>
      </article>
      <article class="mini-card surface-card">
        <span>创作者平台</span>
        <strong>{{ overview.creator_platform_total }}</strong>
      </article>
      <article class="mini-card surface-card">
        <span>创作者总数</span>
        <strong>{{ overview.creator_total }}</strong>
      </article>
    </section>

    <section class="surface-card tab-shell">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="来源平台" name="platforms">
          <section class="toolbar">
            <div class="toolbar-row platform-toolbar-row">
              <el-input v-model="platformFilters.search" placeholder="搜索平台名称 / slug / 说明" clearable />
              <el-select v-model="platformFilters.platform_type" placeholder="全部类型" clearable>
                <el-option label="权威机构" value="official" />
                <el-option label="创作者平台" value="creator" />
                <el-option label="全部类型" value="all" />
              </el-select>
              <el-select v-model="platformFilters.status" placeholder="全部状态" clearable>
                <el-option label="启用" value="active" />
                <el-option label="停用" value="inactive" />
                <el-option label="全部状态" value="all" />
              </el-select>
            </div>

            <div class="toolbar-actions">
              <el-button @click="openCreatePlatformDialog">新增平台</el-button>
              <el-button
                type="danger"
                plain
                :disabled="selectedPlatformIds.length === 0"
                :loading="deletePlatformsLoading"
                @click="deletePlatforms(selectedPlatformIds)"
              >
                批量删除
              </el-button>
              <button class="ghost-btn" @click="resetPlatformFilters">重置筛选</button>
              <el-button type="primary" @click="applyPlatformFilters">查询</el-button>
            </div>
          </section>

          <section class="table-card">
            <div class="table-head">
              <div>
                <span class="section-chip">Platform Matrix</span>
                <h2>来源平台列表</h2>
              </div>
              <el-button @click="fetchPlatforms">刷新数据</el-button>
            </div>

            <el-table
              :data="platformRecords"
              stripe
              row-key="platform_id"
              v-loading="platformsLoading"
              @selection-change="handlePlatformSelectionChange"
            >
              <el-table-column type="selection" width="48" reserve-selection />
              <el-table-column label="平台" min-width="240">
                <template #default="{ row }">
                  <div class="title-cell">
                    <strong>{{ row.name }}</strong>
                    <span>{{ row.slug }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="类型 / 标签" width="160">
                <template #default="{ row }">
                  <div class="meta-cell">
                    <strong>{{ row.platform_type === 'official' ? '权威机构' : '创作者平台' }}</strong>
                    <span>{{ row.badge_text || row.short_label || '未设置' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="说明" min-width="320">
                <template #default="{ row }">
                  <div class="table-preview">{{ row.description || row.scene_hint || row.subtitle || '暂无说明' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="链接 / 状态" min-width="220">
                <template #default="{ row }">
                  <div class="meta-cell">
                    <strong>{{ row.status === 'active' ? '启用中' : '已停用' }}</strong>
                    <span>{{ row.url || '链接待补充' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="sort_order" label="排序" width="90" />
              <el-table-column label="操作" width="180" fixed="right">
                <template #default="{ row }">
                  <el-button type="primary" link @click="openEditPlatformDialog(row)">编辑</el-button>
                  <el-button type="danger" link @click="deletePlatforms([row.platform_id])">删除</el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pagination-wrap">
              <el-pagination
                background
                layout="total, sizes, prev, pager, next"
                :total="platformPagination.total"
                :current-page="platformPagination.page"
                :page-size="platformPagination.pageSize"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="handlePlatformPageChange"
                @size-change="handlePlatformPageSizeChange"
              />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="创作者资料" name="creators">
          <section class="toolbar">
            <div class="toolbar-row creator-toolbar-row">
              <el-input v-model="creatorFilters.search" placeholder="搜索创作者名称 / slug / 定位说明" clearable />
              <el-select v-model="creatorFilters.platform_id" placeholder="全部平台" clearable>
                <el-option
                  v-for="item in creatorPlatformOptions"
                  :key="item.platform_id"
                  :label="item.name"
                  :value="item.platform_id"
                />
                <el-option label="全部平台" value="all" />
              </el-select>
              <el-select v-model="creatorFilters.status" placeholder="全部状态" clearable>
                <el-option label="启用" value="active" />
                <el-option label="停用" value="inactive" />
                <el-option label="全部状态" value="all" />
              </el-select>
            </div>

            <div class="toolbar-actions">
              <el-button @click="openCreateCreatorDialog">新增创作者</el-button>
              <el-button
                type="danger"
                plain
                :disabled="selectedCreatorIds.length === 0"
                :loading="deleteCreatorsLoading"
                @click="deleteCreators(selectedCreatorIds)"
              >
                批量删除
              </el-button>
              <button class="ghost-btn" @click="resetCreatorFilters">重置筛选</button>
              <el-button type="primary" @click="applyCreatorFilters">查询</el-button>
            </div>
          </section>

          <section class="table-card">
            <div class="table-head">
              <div>
                <span class="section-chip">Creator Deck</span>
                <h2>创作者资料列表</h2>
              </div>
              <el-button @click="fetchCreators">刷新数据</el-button>
            </div>

            <el-table
              :data="creatorRecords"
              stripe
              row-key="creator_id"
              v-loading="creatorsLoading"
              @selection-change="handleCreatorSelectionChange"
            >
              <el-table-column type="selection" width="48" reserve-selection />
              <el-table-column label="创作者" min-width="280">
                <template #default="{ row }">
                  <div class="creator-cell">
                    <div class="creator-avatar-shell">
                      <img
                        v-if="creatorAvatar(row)"
                        :src="creatorAvatar(row)"
                        :alt="row.display_name"
                        class="creator-avatar"
                      />
                      <div v-else class="creator-avatar placeholder">
                        {{ creatorInitial(row.display_name) }}
                      </div>
                    </div>
                    <div class="title-cell">
                      <strong>{{ row.display_name }}</strong>
                      <span>{{ row.platform_name || '平台待补充' }} · {{ row.follower_text || '粉丝待补充' }}</span>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="定位 / 标签" min-width="280">
                <template #default="{ row }">
                  <div class="title-cell">
                    <strong>{{ row.positioning || '定位待补充' }}</strong>
                    <span>{{ (row.tags || []).join(' / ') || '暂无标签' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="简介" min-width="320">
                <template #default="{ row }">
                  <div class="table-preview">{{ row.description || '暂无简介' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="链接 / 状态" min-width="220">
                <template #default="{ row }">
                  <div class="meta-cell">
                    <strong>{{ row.status === 'active' ? '启用中' : '已停用' }}</strong>
                    <span>{{ row.profile_url || '链接待补充' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="sort_order" label="排序" width="90" />
              <el-table-column label="操作" width="180" fixed="right">
                <template #default="{ row }">
                  <el-button type="primary" link @click="openEditCreatorDialog(row)">编辑</el-button>
                  <el-button type="danger" link @click="deleteCreators([row.creator_id])">删除</el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pagination-wrap">
              <el-pagination
                background
                layout="total, sizes, prev, pager, next"
                :total="creatorPagination.total"
                :current-page="creatorPagination.page"
                :page-size="creatorPagination.pageSize"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="handleCreatorPageChange"
                @size-change="handleCreatorPageSizeChange"
              />
            </div>
          </section>
        </el-tab-pane>
      </el-tabs>
    </section>

    <el-dialog
      v-model="platformDialogVisible"
      :title="platformDialogMode === 'create' ? '新增来源平台' : '编辑来源平台'"
      width="720px"
      destroy-on-close
    >
      <div class="dialog-shell">
        <div class="dialog-grid double-grid">
          <el-input v-model="platformForm.name" placeholder="平台名称" />
          <el-input v-model="platformForm.slug" placeholder="平台标识 slug，可留空自动生成" />
        </div>
        <div class="dialog-grid double-grid">
          <el-select v-model="platformForm.platform_type" placeholder="平台类型">
            <el-option label="权威机构" value="official" />
            <el-option label="创作者平台" value="creator" />
          </el-select>
          <el-select v-model="platformForm.status" placeholder="状态">
            <el-option label="启用" value="active" />
            <el-option label="停用" value="inactive" />
          </el-select>
        </div>
        <div class="dialog-grid triple-grid">
          <el-input v-model="platformForm.short_label" placeholder="短标签，如 PIYAO" />
          <el-input v-model="platformForm.badge_text" placeholder="徽标标签，如 国家级" />
          <el-input v-model="platformForm.sort_order" placeholder="排序值" />
        </div>
        <div class="dialog-grid double-grid">
          <el-input v-model="platformForm.subtitle" placeholder="副标题 / 平台说明" />
          <el-input v-model="platformForm.theme_token" placeholder="主题标识，如 blue / warm" />
        </div>
        <el-input v-model="platformForm.scene_hint" placeholder="适用场景 / 推荐说明" />
        <el-input v-model="platformForm.url" placeholder="平台链接" />
        <el-input
          v-model="platformForm.description"
          type="textarea"
          :rows="4"
          placeholder="平台简介"
        />
      </div>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="platformDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="savePlatformLoading" @click="submitPlatformForm">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="creatorDialogVisible"
      :title="creatorDialogMode === 'create' ? '新增创作者' : '编辑创作者'"
      width="760px"
      destroy-on-close
    >
      <div class="dialog-shell">
        <div class="dialog-grid double-grid">
          <el-select v-model="creatorForm.platform_id" placeholder="选择创作者平台">
            <el-option
              v-for="item in creatorPlatformOptions"
              :key="item.platform_id"
              :label="item.name"
              :value="item.platform_id"
            />
          </el-select>
          <el-input v-model="creatorForm.display_name" placeholder="创作者名称" />
        </div>
        <div class="dialog-grid double-grid">
          <el-input v-model="creatorForm.slug" placeholder="创作者标识 slug，可留空自动生成" />
          <el-select v-model="creatorForm.status" placeholder="状态">
            <el-option label="启用" value="active" />
            <el-option label="停用" value="inactive" />
          </el-select>
        </div>
        <div class="dialog-grid triple-grid">
          <el-input v-model="creatorForm.follower_text" placeholder="粉丝文本，如 98.6 万关注" />
          <el-input v-model="creatorForm.sort_order" placeholder="排序值" />
          <el-input v-model="creatorForm.avatar_url" placeholder="头像链接，可留空使用占位头像" />
        </div>
        <el-input v-model="creatorForm.positioning" placeholder="定位说明" />
        <el-input v-model="creatorForm.profile_url" placeholder="主页链接" />
        <el-input v-model="creatorForm.tags_text" placeholder="标签，支持用逗号、顿号或换行分隔" />
        <el-input
          v-model="creatorForm.description"
          type="textarea"
          :rows="4"
          placeholder="创作者简介"
        />
      </div>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="creatorDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saveCreatorLoading" @click="submitCreatorForm">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'

import api, { resolveAssetUrl } from '@/api/client'

const router = useRouter()

const activeTab = ref('platforms')
const platformsLoading = ref(false)
const creatorsLoading = ref(false)
const savePlatformLoading = ref(false)
const saveCreatorLoading = ref(false)
const deletePlatformsLoading = ref(false)
const deleteCreatorsLoading = ref(false)
const platformDialogVisible = ref(false)
const creatorDialogVisible = ref(false)
const platformDialogMode = ref('create')
const creatorDialogMode = ref('create')

const overview = reactive({
  platform_total: 0,
  official_total: 0,
  creator_platform_total: 0,
  creator_total: 0,
})

const platformFilters = reactive({
  search: '',
  platform_type: 'all',
  status: 'all',
})

const creatorFilters = reactive({
  search: '',
  platform_id: 'all',
  status: 'all',
})

const platformPagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
})

const creatorPagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
})

const platformRecords = ref([])
const creatorRecords = ref([])
const selectedPlatformIds = ref([])
const selectedCreatorIds = ref([])
const creatorPlatformOptions = ref([])

const createEmptyPlatformForm = () => ({
  platform_id: null,
  name: '',
  slug: '',
  platform_type: 'official',
  short_label: '',
  badge_text: '',
  subtitle: '',
  description: '',
  scene_hint: '',
  url: '',
  theme_token: '',
  sort_order: 0,
  status: 'active',
})

const createEmptyCreatorForm = () => ({
  creator_id: null,
  platform_id: null,
  display_name: '',
  slug: '',
  avatar_url: '',
  follower_text: '',
  positioning: '',
  description: '',
  profile_url: '',
  tags_text: '',
  sort_order: 0,
  status: 'active',
})

const platformForm = reactive(createEmptyPlatformForm())
const creatorForm = reactive(createEmptyCreatorForm())

const platformIdsByType = computed(() => ({
  creator: creatorPlatformOptions.value.map((item) => item.platform_id),
}))

const normalizeTags = (value) => (
  String(value || '')
    .split(/[，,、/\n]+/)
    .map((item) => item.trim())
    .filter(Boolean)
)

const creatorInitial = (name = '') => (name.trim().charAt(0) || '创').toUpperCase()

const creatorAvatar = (row) => (row?.avatar_url ? resolveAssetUrl(row.avatar_url, row.update_time || '') : '')

const fetchOverview = async () => {
  const response = await api.get('/admin/quick-look/overview')
  Object.assign(overview, response.data.data || {})
}

const fetchPlatforms = async () => {
  platformsLoading.value = true
  try {
    const response = await api.get('/admin/quick-look/platforms', {
      params: {
        search: platformFilters.search || undefined,
        platform_type: platformFilters.platform_type || undefined,
        status: platformFilters.status || undefined,
        page: platformPagination.page,
        page_size: platformPagination.pageSize,
      },
    })
    const payload = response.data.data || {}
    platformRecords.value = payload.items || []
    platformPagination.total = Number(payload.total || 0)
    platformPagination.page = Number(payload.page || platformPagination.page)
    platformPagination.pageSize = Number(payload.page_size || platformPagination.pageSize)
    creatorPlatformOptions.value = platformRecords.value
      .filter((item) => item.platform_type === 'creator')
      .map((item) => ({
        platform_id: item.platform_id,
        name: item.name,
        slug: item.slug,
      }))
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '来源平台加载失败')
  } finally {
    platformsLoading.value = false
  }
}

const fetchCreators = async () => {
  creatorsLoading.value = true
  try {
    const response = await api.get('/admin/quick-look/creators', {
      params: {
        search: creatorFilters.search || undefined,
        platform_id: creatorFilters.platform_id === 'all' ? undefined : creatorFilters.platform_id,
        status: creatorFilters.status || undefined,
        page: creatorPagination.page,
        page_size: creatorPagination.pageSize,
      },
    })
    const payload = response.data.data || {}
    creatorRecords.value = payload.items || []
    creatorPagination.total = Number(payload.total || 0)
    creatorPagination.page = Number(payload.page || creatorPagination.page)
    creatorPagination.pageSize = Number(payload.page_size || creatorPagination.pageSize)
    if ((payload.platform_options || []).length > 0) {
      creatorPlatformOptions.value = payload.platform_options
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '创作者资料加载失败')
  } finally {
    creatorsLoading.value = false
  }
}

const refreshAll = async () => {
  await Promise.all([fetchOverview(), fetchPlatforms(), fetchCreators()])
}

const resetPlatformForm = () => {
  Object.assign(platformForm, createEmptyPlatformForm())
}

const resetCreatorForm = () => {
  Object.assign(creatorForm, createEmptyCreatorForm())
}

const normalizePlatformPayload = () => ({
  name: platformForm.name,
  slug: platformForm.slug || undefined,
  platform_type: platformForm.platform_type,
  short_label: platformForm.short_label || undefined,
  badge_text: platformForm.badge_text || undefined,
  subtitle: platformForm.subtitle || undefined,
  description: platformForm.description || undefined,
  scene_hint: platformForm.scene_hint || undefined,
  url: platformForm.url || undefined,
  theme_token: platformForm.theme_token || undefined,
  sort_order: Number(platformForm.sort_order || 0),
  status: platformForm.status,
})

const normalizeCreatorPayload = () => ({
  platform_id: Number(creatorForm.platform_id),
  display_name: creatorForm.display_name,
  slug: creatorForm.slug || undefined,
  avatar_url: creatorForm.avatar_url || undefined,
  follower_text: creatorForm.follower_text || undefined,
  positioning: creatorForm.positioning || undefined,
  description: creatorForm.description || undefined,
  profile_url: creatorForm.profile_url || undefined,
  tags: normalizeTags(creatorForm.tags_text),
  sort_order: Number(creatorForm.sort_order || 0),
  status: creatorForm.status,
})

const openCreatePlatformDialog = () => {
  platformDialogMode.value = 'create'
  resetPlatformForm()
  platformDialogVisible.value = true
}

const openEditPlatformDialog = (row) => {
  platformDialogMode.value = 'edit'
  Object.assign(platformForm, {
    platform_id: row.platform_id,
    name: row.name || '',
    slug: row.slug || '',
    platform_type: row.platform_type || 'official',
    short_label: row.short_label || '',
    badge_text: row.badge_text || '',
    subtitle: row.subtitle || '',
    description: row.description || '',
    scene_hint: row.scene_hint || '',
    url: row.url || '',
    theme_token: row.theme_token || '',
    sort_order: row.sort_order ?? 0,
    status: row.status || 'active',
  })
  platformDialogVisible.value = true
}

const openCreateCreatorDialog = () => {
  creatorDialogMode.value = 'create'
  resetCreatorForm()
  if (creatorPlatformOptions.value.length > 0) {
    creatorForm.platform_id = creatorPlatformOptions.value[0].platform_id
  }
  creatorDialogVisible.value = true
}

const openEditCreatorDialog = (row) => {
  creatorDialogMode.value = 'edit'
  Object.assign(creatorForm, {
    creator_id: row.creator_id,
    platform_id: row.platform_id,
    display_name: row.display_name || '',
    slug: row.slug || '',
    avatar_url: row.avatar_url || '',
    follower_text: row.follower_text || '',
    positioning: row.positioning || '',
    description: row.description || '',
    profile_url: row.profile_url || '',
    tags_text: (row.tags || []).join('，'),
    sort_order: row.sort_order ?? 0,
    status: row.status || 'active',
  })
  creatorDialogVisible.value = true
}

const submitPlatformForm = async () => {
  savePlatformLoading.value = true
  try {
    const payload = normalizePlatformPayload()
    const response = platformDialogMode.value === 'create'
      ? await api.post('/admin/quick-look/platforms', payload, { timeout: 60000 })
      : await api.patch(`/admin/quick-look/platforms/${platformForm.platform_id}`, payload, { timeout: 60000 })
    platformDialogVisible.value = false
    resetPlatformForm()
    await refreshAll()
    ElMessage.success(response.data.message || '平台资料已保存')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '平台资料保存失败')
  } finally {
    savePlatformLoading.value = false
  }
}

const submitCreatorForm = async () => {
  saveCreatorLoading.value = true
  try {
    const payload = normalizeCreatorPayload()
    const response = creatorDialogMode.value === 'create'
      ? await api.post('/admin/quick-look/creators', payload, { timeout: 60000 })
      : await api.patch(`/admin/quick-look/creators/${creatorForm.creator_id}`, payload, { timeout: 60000 })
    creatorDialogVisible.value = false
    resetCreatorForm()
    await refreshAll()
    ElMessage.success(response.data.message || '创作者资料已保存')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '创作者资料保存失败')
  } finally {
    saveCreatorLoading.value = false
  }
}

const deletePlatforms = async (platformIds) => {
  if (!platformIds.length) {
    ElMessage.warning('请先选择需要删除的平台')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认删除这 ${platformIds.length} 个来源平台吗？关联创作者也会一并删除。`,
      '删除来源平台',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }
  deletePlatformsLoading.value = true
  try {
    const response = await api.delete('/admin/quick-look/platforms', {
      data: { platform_ids: platformIds },
      timeout: 60000,
    })
    await refreshAll()
    ElMessage.success(`已删除 ${response.data.data.deleted_count} 个来源平台`)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '删除来源平台失败')
  } finally {
    deletePlatformsLoading.value = false
  }
}

const deleteCreators = async (creatorIds) => {
  if (!creatorIds.length) {
    ElMessage.warning('请先选择需要删除的创作者')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认删除这 ${creatorIds.length} 位创作者吗？`,
      '删除创作者',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }
  deleteCreatorsLoading.value = true
  try {
    const response = await api.delete('/admin/quick-look/creators', {
      data: { creator_ids: creatorIds },
      timeout: 60000,
    })
    await refreshAll()
    ElMessage.success(`已删除 ${response.data.data.deleted_count} 位创作者`)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '删除创作者失败')
  } finally {
    deleteCreatorsLoading.value = false
  }
}

const handlePlatformSelectionChange = (rows) => {
  selectedPlatformIds.value = rows.map((item) => item.platform_id)
}

const handleCreatorSelectionChange = (rows) => {
  selectedCreatorIds.value = rows.map((item) => item.creator_id)
}

const applyPlatformFilters = () => {
  platformPagination.page = 1
  fetchPlatforms()
}

const resetPlatformFilters = () => {
  platformFilters.search = ''
  platformFilters.platform_type = 'all'
  platformFilters.status = 'all'
  platformPagination.page = 1
  fetchPlatforms()
}

const applyCreatorFilters = () => {
  creatorPagination.page = 1
  fetchCreators()
}

const resetCreatorFilters = () => {
  creatorFilters.search = ''
  creatorFilters.platform_id = 'all'
  creatorFilters.status = 'all'
  creatorPagination.page = 1
  fetchCreators()
}

const handlePlatformPageChange = (page) => {
  platformPagination.page = page
  fetchPlatforms()
}

const handlePlatformPageSizeChange = (pageSize) => {
  platformPagination.pageSize = pageSize
  platformPagination.page = 1
  fetchPlatforms()
}

const handleCreatorPageChange = (page) => {
  creatorPagination.page = page
  fetchCreators()
}

const handleCreatorPageSizeChange = (pageSize) => {
  creatorPagination.pageSize = pageSize
  creatorPagination.page = 1
  fetchCreators()
}

onMounted(() => {
  refreshAll()
})
</script>

<style scoped>
.source-admin-page {
  padding: 24px;
  display: grid;
  gap: 18px;
}

.source-admin-top,
.mini-card,
.tab-shell {
  padding: 24px;
  border-radius: 28px;
}

.source-admin-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
}

.section-chip {
  display: inline-flex;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(15, 123, 255, 0.08);
  color: var(--brand-deep);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.source-admin-top h1,
.table-head h2 {
  margin: 14px 0 8px;
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1.08;
  letter-spacing: -0.04em;
  color: var(--ink-strong);
}

.source-admin-top p {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.8;
}

.top-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.ghost-btn {
  border: 1px solid var(--line-soft);
  background: rgba(255, 255, 255, 0.84);
  color: var(--ink-main);
  padding: 12px 18px;
  border-radius: 16px;
  cursor: pointer;
  transition: 0.22s ease;
}

.ghost-btn:hover {
  transform: translateY(-1px);
  border-color: rgba(15, 123, 255, 0.22);
}

.mini-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.mini-card {
  background:
    radial-gradient(circle at top right, rgba(15, 123, 255, 0.1), transparent 32%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.96));
}

.mini-card span {
  color: var(--ink-soft);
  font-size: 13px;
}

.mini-card strong {
  display: block;
  margin-top: 10px;
  font-size: 30px;
  color: var(--ink-strong);
}

.tab-shell :deep(.el-tabs__header) {
  margin-bottom: 22px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin-bottom: 18px;
}

.toolbar-row {
  flex: 1;
  display: grid;
  gap: 12px;
}

.platform-toolbar-row {
  grid-template-columns: minmax(260px, 1fr) 180px 180px;
}

.creator-toolbar-row {
  grid-template-columns: minmax(260px, 1fr) 220px 180px;
}

.toolbar-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.toolbar :deep(.el-input__wrapper),
.toolbar :deep(.el-select__wrapper),
.dialog-shell :deep(.el-input__wrapper),
.dialog-shell :deep(.el-select__wrapper),
.dialog-shell :deep(.el-textarea__inner) {
  min-height: 44px;
  border-radius: 14px;
  box-shadow: none;
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.table-card :deep(.el-table) {
  border-radius: 18px;
  overflow: hidden;
}

.table-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 18px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 18px;
}

.title-cell,
.meta-cell {
  display: grid;
  gap: 6px;
}

.title-cell strong {
  color: var(--ink-strong);
  font-size: 15px;
  line-height: 1.5;
}

.title-cell span,
.meta-cell span {
  color: var(--ink-soft);
  font-size: 12px;
  line-height: 1.6;
}

.meta-cell strong {
  color: var(--ink-main);
  line-height: 1.6;
}

.table-preview {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
  line-height: 1.7;
}

.creator-cell {
  display: grid;
  grid-template-columns: 60px 1fr;
  gap: 12px;
  align-items: center;
}

.creator-avatar-shell {
  width: 60px;
  height: 60px;
}

.creator-avatar {
  width: 60px;
  height: 60px;
  border-radius: 18px;
  object-fit: cover;
  display: block;
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.creator-avatar.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  border-radius: 18px;
  background: linear-gradient(135deg, #ff8a3d, #f97316);
  color: #fff;
  font-size: 24px;
  font-weight: 800;
}

.dialog-shell {
  display: grid;
  gap: 14px;
}

.dialog-grid {
  display: grid;
  gap: 14px;
}

.dialog-grid.double-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.dialog-grid.triple-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 1280px) {
  .mini-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1080px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-row,
  .platform-toolbar-row,
  .creator-toolbar-row,
  .dialog-grid.double-grid,
  .dialog-grid.triple-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .source-admin-page {
    padding: 14px;
  }

  .source-admin-top,
  .mini-card,
  .tab-shell {
    padding: 18px;
    border-radius: 22px;
  }

  .source-admin-top,
  .top-actions,
  .table-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .mini-grid {
    grid-template-columns: 1fr;
  }

  .creator-cell {
    grid-template-columns: 1fr;
  }
}
</style>
