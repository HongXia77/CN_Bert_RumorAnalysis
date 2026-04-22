<template>
  <div class="admin-page">
    <header class="admin-top surface-card">
      <div>
        <span class="section-chip">Admin Console</span>
        <h1>用户与谣言知识库管理</h1>
        <p>管理员可以在同一工作台里完成成员治理、主谣言维护、平台数据导入与详情核查。</p>
      </div>

      <div class="top-actions">
        <button class="ghost-btn" @click="router.push('/rumor_library')">公开谣言页</button>
        <button class="ghost-btn" @click="router.push('/data_analysis')">系统分析</button>
        <button class="ghost-btn" @click="router.push('/main')">返回主页</button>
      </div>
    </header>

    <section class="mini-grid">
      <article class="mini-card surface-card">
        <span>用户总数</span>
        <strong>{{ overview.user_stats.total }}</strong>
      </article>
      <article class="mini-card surface-card">
        <span>管理员</span>
        <strong>{{ overview.user_stats.admin }}</strong>
      </article>
      <article class="mini-card surface-card">
        <span>正常账号</span>
        <strong>{{ overview.user_stats.active }}</strong>
      </article>
      <article class="mini-card surface-card">
        <span>谣言总数</span>
        <strong>{{ overview.rumor_stats.total }}</strong>
      </article>
      <article class="mini-card surface-card">
        <span>平台谣言</span>
        <strong>{{ overview.rumor_stats.system }}</strong>
      </article>
        <article class="mini-card surface-card">
          <span>待复核记录</span>
          <strong>{{ overview.upload_review_stats.pending }}</strong>
        </article>
    </section>

    <section class="surface-card admin-tabs">
      <el-tabs v-model="activePanel">
        <el-tab-pane label="用户管理" name="users">
          <section class="toolbar">
            <div class="toolbar-row">
              <el-input v-model="userFilters.search" placeholder="搜索用户名 / 邮箱 / 手机号" clearable />
              <el-select v-model="userFilters.role" placeholder="全部角色" clearable>
                <el-option label="管理员" value="admin" />
                <el-option label="普通用户" value="user" />
              </el-select>
              <el-select v-model="userFilters.status" placeholder="全部状态" clearable>
                <el-option label="正常" value="正常" />
                <el-option label="禁用" value="禁用" />
                <el-option label="未激活" value="未激活" />
              </el-select>
            </div>

            <div class="toolbar-actions">
              <el-upload
                :show-file-list="false"
                :http-request="uploadUsersWorkbook"
                accept=".xlsx"
              >
                <el-button :loading="importUsersLoading">导入 Excel</el-button>
              </el-upload>
              <el-button :loading="exportUsersLoading" @click="exportUsers">导出用户</el-button>
              <el-button @click="downloadImportTemplate">下载模板</el-button>
              <el-button
                type="danger"
                plain
                :disabled="selectedUserIds.length === 0"
                :loading="deleteUsersLoading"
                @click="deleteUsers(selectedUserIds)"
              >
                批量删除
              </el-button>
              <button class="ghost-btn" @click="resetUserFilters">重置筛选</button>
              <el-button type="primary" @click="applyUserFilters">查询</el-button>
            </div>
          </section>

          <section class="table-card">
            <div class="table-head">
              <div>
                <span class="section-chip">Members</span>
                <h2>系统成员列表</h2>
              </div>
              <el-button @click="refreshAll">刷新数据</el-button>
            </div>

            <el-table
              :data="users"
              stripe
              row-key="user_id"
              v-loading="usersLoading"
              @selection-change="handleUserSelectionChange"
            >
              <el-table-column type="selection" width="48" reserve-selection />
              <el-table-column prop="username" label="用户名" min-width="140" />
              <el-table-column prop="email" label="邮箱" min-width="210" />
              <el-table-column prop="phone" label="手机号" min-width="150" />
              <el-table-column label="角色" width="150">
                <template #default="{ row }">
                  <el-select v-model="row.role" size="small">
                    <el-option label="管理员" value="admin" />
                    <el-option label="普通用户" value="user" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="150">
                <template #default="{ row }">
                  <el-select v-model="row.status" size="small">
                    <el-option label="正常" value="正常" />
                    <el-option label="禁用" value="禁用" />
                    <el-option label="未激活" value="未激活" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column prop="create_time" label="创建时间" min-width="180" />
              <el-table-column label="操作" width="180" fixed="right">
                <template #default="{ row }">
                  <el-button type="primary" link @click="saveUser(row)">保存</el-button>
                  <el-button type="danger" link @click="deleteUsers([row.user_id])">删除</el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pagination-wrap">
              <el-pagination
                background
                layout="total, sizes, prev, pager, next"
                :total="userPagination.total"
                :current-page="userPagination.page"
                :page-size="userPagination.pageSize"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="handleUserPageChange"
                @size-change="handleUserPageSizeChange"
              />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="谣言管理" name="rumors">
          <section class="toolbar">
            <div class="toolbar-row rumor-toolbar-row">
              <el-input v-model="rumorFilters.search" placeholder="搜索标题 / 核心断言 / 辟谣摘要" clearable />
              <el-select v-model="rumorFilters.source_type" placeholder="全部来源类型" clearable>
                <el-option label="平台录入" value="system" />
                <el-option label="用户沉淀" value="user" />
              </el-select>
              <el-select v-model="rumorFilters.status" placeholder="全部状态" clearable>
                <el-option label="已通过" value="pass" />
                <el-option label="待审核" value="not_pass" />
              </el-select>
              <el-input v-model="rumorFilters.source_name" placeholder="来源平台" clearable />
            </div>

            <div class="toolbar-actions">
              <el-button :loading="importRumorsLoading" @click="importPiyaoRumors">导入本地平台数据</el-button>
              <el-button @click="openCreateRumorDialog">新增谣言</el-button>
              <el-button
                type="danger"
                plain
                :disabled="selectedRumorIds.length === 0"
                :loading="deleteRumorsLoading"
                @click="deleteRumors(selectedRumorIds)"
              >
                批量删除
              </el-button>
              <button class="ghost-btn" @click="resetRumorFilters">重置筛选</button>
              <el-button type="primary" @click="applyRumorFilters">查询</el-button>
            </div>
          </section>

          <section class="rumor-brief-grid">
            <article class="brief-card surface-card">
              <span>平台条目</span>
              <strong>{{ overview.rumor_stats.system }}</strong>
              <p>支撑用户侧公开谣言库浏览和 Top-K 主谣言候选返回。</p>
            </article>
            <article class="brief-card surface-card">
              <span>用户沉淀</span>
              <strong>{{ overview.rumor_stats.user }}</strong>
              <p>来自用户识别、归并与人工复核后的沉淀结果。</p>
            </article>
            <article class="brief-card surface-card">
              <span>待审核</span>
              <strong>{{ overview.rumor_stats.pending }}</strong>
              <p>建议优先处理来源不明、待合并或尚未确认的条目。</p>
            </article>
          </section>

          <section class="table-card">
            <div class="table-head">
              <div>
                <span class="section-chip">Rumor Library</span>
                <h2>主谣言知识库</h2>
              </div>
              <el-button @click="refreshAll">刷新数据</el-button>
            </div>

            <el-table
              :data="rumors"
              stripe
              row-key="rumor_id"
              v-loading="rumorsLoading"
              @selection-change="handleRumorSelectionChange"
            >
              <el-table-column type="selection" width="48" reserve-selection />
              <el-table-column label="标题" min-width="260">
                <template #default="{ row }">
                  <div class="title-cell">
                    <strong>{{ row.title || '未设置标题' }}</strong>
                    <span>{{ row.claim_text || row.content || '暂无核心断言' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="核心断言" min-width="240">
                <template #default="{ row }">
                  <div class="table-preview">{{ row.content || '暂无' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="辟谣摘要" min-width="280">
                <template #default="{ row }">
                  <div class="table-preview">{{ row.truth_text || '当前暂无辟谣摘要' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="来源 / 发布时间" min-width="210">
                <template #default="{ row }">
                  <div class="meta-cell">
                    <strong>{{ row.source_name || '--' }}</strong>
                    <span>{{ row.publish_time || '--' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="来源类型" width="120">
                <template #default="{ row }">
                  <el-tag :type="row.source_type === 'system' ? 'success' : 'warning'">
                    {{ row.source_type === 'system' ? '平台录入' : '用户沉淀' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="120">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'pass' ? 'primary' : 'danger'">
                    {{ row.status === 'pass' ? '已通过' : '待审核' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="upload_count" label="上传关联" width="100" />
              <el-table-column label="操作" width="220" fixed="right">
                <template #default="{ row }">
                  <el-button type="info" link @click="openRumorDetail(row)">详情</el-button>
                  <el-button type="primary" link @click="openEditRumorDialog(row)">编辑</el-button>
                  <el-button type="danger" link @click="deleteRumors([row.rumor_id])">删除</el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pagination-wrap">
              <el-pagination
                background
                layout="total, sizes, prev, pager, next"
                :total="rumorPagination.total"
                :current-page="rumorPagination.page"
                :page-size="rumorPagination.pageSize"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="handleRumorPageChange"
                @size-change="handleRumorPageSizeChange"
              />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane name="reviews">
          <template #label>
            <div class="review-tab-label">
              <span>审核记录</span>
              <button
                class="tab-inline-action"
                type="button"
                @click.stop="router.push('/admin/quick_sources')"
              >
                速看来源配置
              </button>
            </div>
          </template>
          <section class="toolbar">
            <div class="toolbar-row review-toolbar-row">
              <el-input v-model="reviewFilters.search" placeholder="搜索用户、邮箱、上传文本或审核说明" clearable />
              <el-select v-model="reviewFilters.status" placeholder="全部状态" clearable>
                  <el-option label="待复核" value="待合并" />
                  <el-option label="已合并" value="已合并" />
                  <el-option label="无效" value="无效" />
                  <el-option label="全部状态" value="all" />
                </el-select>
              <el-select v-model="reviewFilters.risk_level" placeholder="全部风险等级" clearable>
                <el-option label="高风险" value="high" />
                <el-option label="需复核" value="medium" />
                <el-option label="较稳定" value="low" />
                <el-option label="全部等级" value="all" />
              </el-select>
            </div>

            <div class="toolbar-actions">
              <button class="ghost-btn" @click="resetReviewFilters">重置筛选</button>
              <el-button type="primary" @click="applyReviewFilters">查询</el-button>
              <el-button @click="fetchReviews">刷新审核列表</el-button>
            </div>
          </section>

          <section class="review-brief-grid">
            <article class="brief-card surface-card">
              <span>待复核</span>
              <strong>{{ overview.upload_review_stats.pending }}</strong>
              <p>尚未确认归并去向的用户识别记录，建议优先检查高风险文本。</p>
            </article>
            <article class="brief-card surface-card">
              <span>高风险待复核</span>
              <strong>{{ overview.upload_review_stats.high_risk_pending }}</strong>
              <p>这部分记录更可能与已知谣言或新谣言热点有关，建议优先审核。</p>
            </article>
            <article class="brief-card surface-card">
              <span>已审核合并</span>
              <strong>{{ overview.upload_review_stats.merged }}</strong>
              <p>管理员已确认并入主谣言的记录数，会反映在对应主谣言上传关联中。</p>
            </article>
            <article class="brief-card surface-card">
              <span>已标无效</span>
              <strong>{{ overview.upload_review_stats.invalid }}</strong>
              <p>未命中已知主谣言或确认不纳入主库的普通查询文本数量。</p>
            </article>
          </section>

          <section class="table-card">
            <div class="table-head">
              <div>
                <span class="section-chip">Review Records</span>
                <h2>上传审核记录</h2>
              </div>
              <el-button @click="fetchReviews">刷新数据</el-button>
            </div>

            <el-table
              :data="reviewRecords"
              stripe
              row-key="upload_id"
              v-loading="reviewsLoading"
            >
              <el-table-column label="用户" min-width="180">
                <template #default="{ row }">
                  <div class="meta-cell">
                    <strong>{{ row.username || `用户 #${row.user_id}` }}</strong>
                    <span>{{ row.email || '邮箱待补充' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="上传文本" min-width="300">
                <template #default="{ row }">
                  <div class="title-cell">
                    <strong>{{ row.verdict }}</strong>
                    <span class="table-preview">{{ row.text }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="风险结果" width="190">
                <template #default="{ row }">
                  <div class="review-risk-cell">
                    <el-tag :type="riskTagType(row.risk_level)" effect="dark" round>
                      {{ riskLabel(row.risk_level) }}
                    </el-tag>
                    <span>谣言概率 {{ formatReviewPercent(row.rumor_probability) }}</span>
                    <span>匹配概率 {{ formatReviewPercent(row.event_match_probability) }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="建议主谣言" min-width="240">
                <template #default="{ row }">
                  <div class="title-cell">
                    <strong>{{ reviewSuggestedTitle(row) }}</strong>
                    <span>{{ reviewSuggestedHint(row) }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="状态 / 时间" width="200">
                <template #default="{ row }">
                  <div class="meta-cell">
                    <strong>{{ row.upload_status }}</strong>
                    <span>{{ row.createdAt }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="240" fixed="right">
                <template #default="{ row }">
                  <el-button type="info" link @click="openReviewDetail(row)">详情</el-button>
                  <el-button
                    v-if="row.upload_status === '待合并' && row.review_target_rumor_id"
                    type="primary"
                    link
                    :loading="reviewActionLoading && reviewActionTargetId === row.upload_id"
                    @click="quickMergeReview(row)"
                  >
                    并入建议候选
                  </el-button>
                  <el-button
                    v-if="row.upload_status !== '无效'"
                    type="danger"
                    link
                    :loading="reviewActionLoading && reviewActionTargetId === row.upload_id"
                    @click="markReviewInvalid(row)"
                  >
                    标记无效
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pagination-wrap">
              <el-pagination
                background
                layout="total, sizes, prev, pager, next"
                :total="reviewPagination.total"
                :current-page="reviewPagination.page"
                :page-size="reviewPagination.pageSize"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="handleReviewPageChange"
                @size-change="handleReviewPageSizeChange"
              />
            </div>
          </section>
        </el-tab-pane>
      </el-tabs>
    </section>

    <el-drawer
      v-model="rumorDetailVisible"
      size="44%"
      destroy-on-close
      class="rumor-detail-drawer"
    >
      <template #header>
        <div v-if="activeRumorDetail" class="drawer-head">
          <span class="section-chip">Rumor Detail</span>
          <h2>{{ activeRumorDetail.title || activeRumorDetail.content || '主谣言详情' }}</h2>
          <p>
            {{ activeRumorDetail.source_name || '来源待补充' }}
            <span v-if="activeRumorDetail.publish_time"> · {{ activeRumorDetail.publish_time }}</span>
          </p>
        </div>
      </template>

      <div v-if="activeRumorDetail" class="drawer-body">
        <section class="drawer-section surface-card">
          <div class="drawer-section-head">
            <span>结构化信息</span>
            <el-tag :type="activeRumorDetail.source_type === 'system' ? 'success' : 'warning'" effect="plain" round>
              {{ activeRumorDetail.source_type === 'system' ? '平台录入' : '用户沉淀' }}
            </el-tag>
          </div>

          <div class="meta-grid">
            <div>
              <label>文章 ID</label>
              <p>{{ activeRumorDetail.article_id || '--' }}</p>
            </div>
            <div>
              <label>状态</label>
              <p>{{ activeRumorDetail.status === 'pass' ? '已通过' : '待审核' }}</p>
            </div>
            <div>
              <label>上传关联</label>
              <p>{{ activeRumorDetail.upload_count ?? 0 }}</p>
            </div>
            <div>
              <label>识别标签</label>
              <p>{{ activeRumorDetail.label === 1 ? '谣言' : '非谣言' }}</p>
            </div>
          </div>
        </section>

        <section class="drawer-section surface-card">
          <span class="detail-label">核心断言</span>
          <p>{{ activeRumorDetail.content || '暂无' }}</p>
        </section>

        <section class="drawer-section surface-card">
          <span class="detail-label">辟谣摘要</span>
          <p>{{ activeRumorDetail.truth_text || '暂无辟谣摘要' }}</p>
        </section>

        <section class="drawer-section surface-card">
          <div class="drawer-section-head">
            <span>原始正文</span>
            <a
              v-if="activeRumorDetail.article_url"
              :href="activeRumorDetail.article_url"
              target="_blank"
              rel="noreferrer"
            >
              打开原文
            </a>
          </div>
          <p class="long-text">{{ activeRumorDetail.raw_content || '当前未保存原始正文。' }}</p>
        </section>
      </div>
    </el-drawer>

    <el-dialog
      v-model="rumorDialogVisible"
      :title="rumorDialogMode === 'create' ? '新增谣言条目' : '编辑谣言条目'"
      width="860px"
    >
      <div class="dialog-shell">
        <section class="dialog-panel">
          <div class="panel-headline">
            <span class="section-chip">Editable Fields</span>
            <p>这里保留日常维护最常用的结构化字段，原始正文已移到详情抽屉中查看。</p>
          </div>

          <div class="dialog-grid double-grid">
            <el-input v-model="rumorForm.title" placeholder="主谣言标题" />
            <el-input v-model="rumorForm.source_name" placeholder="来源平台或出处" />
            <el-input v-model="rumorForm.content" placeholder="核心匹配文本" />
            <el-input v-model="rumorForm.claim_text" placeholder="抽取的谣言断言" />
            <el-input v-model="rumorForm.article_id" placeholder="文章唯一标识 article_id" />
            <el-input v-model="rumorForm.article_url" placeholder="文章原始链接" />
            <el-input v-model="rumorForm.publish_time" placeholder="发布时间，例如 2026-04-17 16:07:44" />
            <el-select v-model="rumorForm.source_type" placeholder="来源类型">
              <el-option label="平台录入" value="system" />
              <el-option label="用户沉淀" value="user" />
            </el-select>
            <el-select v-model="rumorForm.status" placeholder="审核状态">
              <el-option label="已通过" value="pass" />
              <el-option label="待审核" value="not_pass" />
            </el-select>
            <el-select v-model="rumorForm.label" placeholder="标签">
              <el-option label="谣言" :value="1" />
              <el-option label="非谣言" :value="0" />
            </el-select>
          </div>
        </section>

        <section class="dialog-panel">
          <div class="panel-headline">
            <span class="section-chip">Truth Summary</span>
            <p>这个摘要会直接影响用户侧谣言库、识别候选卡片和详情页的可读性。</p>
          </div>

          <div class="dialog-grid">
            <el-input
              v-model="rumorForm.truth_text"
              type="textarea"
              :rows="5"
              placeholder="辟谣结论 / 真相摘要"
            />
          </div>
        </section>
      </div>

      <template #footer>
        <div class="dialog-actions">
          <el-button @click="rumorDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saveRumorLoading" @click="submitRumorForm">
            保存
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-drawer
      v-model="reviewDetailVisible"
      size="48%"
      destroy-on-close
      class="review-detail-drawer"
    >
      <template #header>
        <div v-if="activeReviewDetail" class="drawer-head">
          <span class="section-chip">Review Detail</span>
          <h2>{{ activeReviewDetail.username || `用户 #${activeReviewDetail.user_id}` }} 的审核记录</h2>
          <p>
            {{ activeReviewDetail.createdAt }}
            <span v-if="activeReviewDetail.email"> · {{ activeReviewDetail.email }}</span>
          </p>
        </div>
      </template>

      <div v-if="activeReviewDetail" class="drawer-body">
        <section class="drawer-section surface-card">
          <div class="drawer-section-head">
            <span>识别结果概览</span>
            <el-tag :type="riskTagType(activeReviewDetail.risk_level)" effect="dark" round>
              {{ riskLabel(activeReviewDetail.risk_level) }}
            </el-tag>
          </div>
          <div class="meta-grid review-meta-grid">
            <div>
              <label>谣言概率</label>
              <p>{{ formatReviewPercent(activeReviewDetail.rumor_probability) }}</p>
            </div>
            <div>
              <label>匹配概率</label>
              <p>{{ formatReviewPercent(activeReviewDetail.event_match_probability) }}</p>
            </div>
            <div>
              <label>当前状态</label>
              <p>{{ activeReviewDetail.upload_status }}</p>
            </div>
            <div>
              <label>审核说明</label>
              <p>{{ activeReviewDetail.merge_reason || '暂无说明' }}</p>
            </div>
          </div>
        </section>

        <section class="drawer-section surface-card">
          <span class="detail-label">用户原始文本</span>
          <p class="long-text">{{ activeReviewDetail.text }}</p>
        </section>

        <section class="drawer-section surface-card">
          <div class="drawer-section-head">
            <span>当前绑定状态</span>
            <el-tag v-if="activeReviewDetail.merged_rumor" type="success" effect="plain" round>已并入主谣言</el-tag>
            <el-tag v-else-if="activeReviewDetail.candidate_rumor" type="warning" effect="plain" round>存在建议候选</el-tag>
            <el-tag v-else type="info" effect="plain" round>暂无官方候选</el-tag>
          </div>
          <div class="review-binding-grid">
            <article class="review-binding-card">
              <label>已并入</label>
              <strong>{{ activeReviewDetail.merged_rumor?.title || '暂无' }}</strong>
              <p>{{ activeReviewDetail.merged_rumor?.content || '当前还没有正式并入主谣言。' }}</p>
            </article>
            <article class="review-binding-card">
              <label>建议候选</label>
              <strong>{{ activeReviewDetail.candidate_rumor?.title || reviewSuggestedTitle(activeReviewDetail) }}</strong>
              <p>{{ activeReviewDetail.candidate_rumor?.content || reviewSuggestedHint(activeReviewDetail) }}</p>
            </article>
          </div>
        </section>

        <section class="drawer-section surface-card">
          <div class="drawer-section-head">
            <span>系统返回的候选主谣言</span>
            <button class="ghost-btn" @click="seedReviewRumorSearch">同步到下方搜索</button>
          </div>
          <div v-if="activeReviewDetail.related_rumors?.length" class="review-candidate-list">
            <article
              v-for="candidate in activeReviewDetail.related_rumors"
              :key="`${candidate.rumor_id || candidate.event_id || candidate.title}`"
              class="review-candidate-card"
            >
              <div class="review-candidate-meta">
                <strong>{{ candidate.title || candidate.content }}</strong>
                <span>{{ candidate.source_name || '候选主谣言' }}</span>
              </div>
              <p>{{ candidate.match_hint || candidate.truth_text || '可继续人工核查。' }}</p>
              <div class="review-candidate-actions">
                <span>关联度 {{ formatMatchScore(candidate.match_score) }}</span>
                <el-button
                  v-if="activeReviewDetail.upload_status === '待合并' && candidate.rumor_id"
                  type="primary"
                  link
                  :loading="reviewActionLoading && reviewActionTargetId === activeReviewDetail.upload_id"
                  @click="submitReviewAction(activeReviewDetail, { action: 'merge', rumor_id: candidate.rumor_id })"
                >
                  并入这条主谣言
                </el-button>
              </div>
            </article>
          </div>
          <el-empty v-else description="当前没有返回可直接审核的候选主谣言。" />
        </section>

        <section class="drawer-section surface-card">
          <div class="drawer-section-head">
            <span>手动指定主谣言</span>
            <el-button :loading="reviewRumorSearchLoading" @click="searchReviewRumors">搜索主谣言</el-button>
          </div>

          <div class="dialog-grid double-grid">
            <el-input
              v-model="reviewRumorSearch"
              placeholder="输入关键词搜索主谣言标题、断言或来源"
              @keyup.enter="searchReviewRumors"
            />
            <el-input
              v-model="reviewActionReason"
              placeholder="可选：补充审核说明，留空则使用系统默认文案"
            />
          </div>

          <div v-if="reviewRumorSearchResults.length" class="review-search-results">
            <article
              v-for="item in reviewRumorSearchResults"
              :key="item.rumor_id"
              class="review-search-card"
            >
              <div class="review-candidate-meta">
                <strong>{{ item.title || item.content }}</strong>
                <span>{{ item.source_name || '来源待补充' }}</span>
              </div>
              <p>{{ item.truth_text || item.content }}</p>
              <div class="review-candidate-actions">
                <span>{{ item.publish_time || '时间待补充' }}</span>
                <el-button
                  v-if="activeReviewDetail.upload_status === '待合并'"
                  type="primary"
                  link
                  :loading="reviewActionLoading && reviewActionTargetId === activeReviewDetail.upload_id"
                  @click="submitReviewAction(activeReviewDetail, { action: 'merge', rumor_id: item.rumor_id, reason: reviewActionReason })"
                >
                  并入该主谣言
                </el-button>
              </div>
            </article>
          </div>

          <div class="review-footer-actions">
            <el-button
              v-if="activeReviewDetail.upload_status !== '待合并'"
              type="warning"
              plain
              :loading="reviewActionLoading && reviewActionTargetId === activeReviewDetail.upload_id"
              @click="submitReviewAction(activeReviewDetail, { action: 'pending', reason: reviewActionReason })"
            >
              保持待复核
            </el-button>
            <el-button
              v-if="activeReviewDetail.upload_status !== '无效'"
              type="danger"
              plain
              :loading="reviewActionLoading && reviewActionTargetId === activeReviewDetail.upload_id"
              @click="submitReviewAction(activeReviewDetail, { action: 'invalid', reason: reviewActionReason })"
            >
              标记无效
            </el-button>
          </div>
        </section>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import api from '@/api/client'

const router = useRouter()

const activePanel = ref('users')
const usersLoading = ref(false)
const rumorsLoading = ref(false)
const reviewsLoading = ref(false)
const importUsersLoading = ref(false)
const exportUsersLoading = ref(false)
const deleteUsersLoading = ref(false)
const importRumorsLoading = ref(false)
const deleteRumorsLoading = ref(false)
const saveRumorLoading = ref(false)
const reviewActionLoading = ref(false)
const reviewActionTargetId = ref(null)
const rumorDialogVisible = ref(false)
const rumorDialogMode = ref('create')
const rumorDetailVisible = ref(false)
const activeRumorDetail = ref(null)
const reviewDetailVisible = ref(false)
const activeReviewDetail = ref(null)
const reviewRumorSearchLoading = ref(false)
const reviewRumorSearch = ref('')
const reviewRumorSearchResults = ref([])
const reviewActionReason = ref('')

const overview = ref({
  user_stats: { total: 0, admin: 0, active: 0, disabled: 0, pending: 0 },
  rumor_stats: { total: 0, approved: 0, pending: 0, system: 0, user: 0, ratio: { rumor: 0, normal: 0 } },
  upload_review_stats: { total: 0, pending: 0, merged: 0, invalid: 0, high_risk_pending: 0 },
})

const users = ref([])
const rumors = ref([])
const reviewRecords = ref([])
const selectedUserIds = ref([])
const selectedRumorIds = ref([])
const userPagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
})
const rumorPagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
})
const reviewPagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
})

const userFilters = reactive({
  search: '',
  role: '',
  status: '',
})

const rumorFilters = reactive({
  search: '',
  source_type: '',
  status: '',
  source_name: '',
})

const reviewFilters = reactive({
  search: '',
  status: 'all',
  risk_level: '',
})

const createEmptyRumorForm = () => ({
  rumor_id: null,
  title: '',
  content: '',
  claim_text: '',
  truth_text: '',
  raw_content: '',
  source_name: '',
  article_id: '',
  article_url: '',
  publish_time: '',
  label: 1,
  status: 'pass',
  source_type: 'system',
})

const rumorForm = reactive(createEmptyRumorForm())

const getBinaryFilename = (headers, fallbackName) => {
  const contentDisposition = headers?.['content-disposition'] || headers?.['Content-Disposition'] || ''
  const encodedMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (encodedMatch?.[1]) {
    return decodeURIComponent(encodedMatch[1])
  }

  const plainMatch = contentDisposition.match(/filename="?([^"]+)"?/i)
  return plainMatch?.[1] || fallbackName
}

const downloadBlobResponse = (response, fallbackName) => {
  const filename = getBinaryFilename(response.headers, fallbackName)
  const blobUrl = window.URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(blobUrl)
}

const extractErrorPayload = (error, fallbackMessage) => {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') {
    return { message: detail, errors: [] }
  }
  if (detail?.message) {
    return detail
  }
  return { message: fallbackMessage, errors: [] }
}

const buildImportSummaryHtml = (payload = {}, title) => {
  const summary = payload.summary || payload
  const lines = [
    `<strong>${title}</strong>`,
    `有效数据行：${summary.total_rows ?? 0}`,
    `空白行：${summary.blank_rows ?? 0}`,
    `新增：${summary.created ?? 0}`,
    `更新：${summary.updated ?? 0}`,
    `失败：${summary.failed ?? 0}`,
  ]

  const errorList = payload.errors || []
  if (errorList.length > 0) {
    lines.push('')
    lines.push('错误明细：')
    errorList.forEach((item) => {
      lines.push(item)
    })
  }

  return lines.join('<br/>')
}

const normalizeRumorPayload = (payload) => {
  const nextPayload = {}
  Object.entries(payload).forEach(([key, value]) => {
    if (typeof value === 'string') {
      nextPayload[key] = value.trim() || null
    } else {
      nextPayload[key] = value
    }
  })
  return nextPayload
}

const riskLabel = (value) => ({
  high: '高风险',
  medium: '需复核',
  low: '较稳定',
}[value] || '待判断')

const riskTagType = (value) => ({
  high: 'danger',
  medium: 'warning',
  low: 'success',
}[value] || 'info')

const formatReviewPercent = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`

const formatMatchScore = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`

const getReviewSuggestedCandidate = (row) => {
  if (row.candidate_rumor) {
    return row.candidate_rumor
  }
  if (Array.isArray(row.related_rumors)) {
    return row.related_rumors.find((item) => item.rumor_id) || row.related_rumors[0] || null
  }
  return null
}

const reviewSuggestedTitle = (row) => {
  const candidate = getReviewSuggestedCandidate(row)
  return candidate?.title || candidate?.content || '暂无明确主谣言候选'
}

const reviewSuggestedHint = (row) => {
  const candidate = getReviewSuggestedCandidate(row)
  if (!candidate) {
    return row.merge_reason || '当前没有找到可直接并入的官方主谣言。'
  }
  return candidate.match_hint || candidate.truth_text || '可作为建议主谣言继续核查。'
}

const resetRumorForm = () => {
  Object.assign(rumorForm, createEmptyRumorForm())
}

const fetchOverview = async () => {
  const response = await api.get('/admin/overview')
  overview.value = response.data.data
}

const fetchUsers = async () => {
  usersLoading.value = true
  try {
    const response = await api.get('/admin/users', {
      params: {
        search: userFilters.search || undefined,
        role: userFilters.role || undefined,
        status: userFilters.status || undefined,
        page: userPagination.page,
        page_size: userPagination.pageSize,
      },
    })
    const payload = response.data.data || {}
    users.value = payload.items || []
    userPagination.total = Number(payload.total || 0)
    userPagination.page = Number(payload.page || userPagination.page)
    userPagination.pageSize = Number(payload.page_size || userPagination.pageSize)
    selectedUserIds.value = []

    const maxPage = Math.max(1, Math.ceil(userPagination.total / userPagination.pageSize))
    if (userPagination.page > maxPage) {
      userPagination.page = maxPage
      await fetchUsers()
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '用户列表获取失败')
  } finally {
    usersLoading.value = false
  }
}

const fetchRumors = async () => {
  rumorsLoading.value = true
  try {
    const response = await api.get('/admin/rumors', {
      params: {
        search: rumorFilters.search || undefined,
        source_type: rumorFilters.source_type || undefined,
        status: rumorFilters.status || undefined,
        source_name: rumorFilters.source_name || undefined,
        page: rumorPagination.page,
        page_size: rumorPagination.pageSize,
      },
    })
    const payload = response.data.data || {}
    rumors.value = payload.items || []
    rumorPagination.total = Number(payload.total || 0)
    rumorPagination.page = Number(payload.page || rumorPagination.page)
    rumorPagination.pageSize = Number(payload.page_size || rumorPagination.pageSize)
    selectedRumorIds.value = []

    const maxPage = Math.max(1, Math.ceil(rumorPagination.total / rumorPagination.pageSize))
    if (rumorPagination.page > maxPage) {
      rumorPagination.page = maxPage
      await fetchRumors()
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '谣言列表获取失败')
  } finally {
    rumorsLoading.value = false
  }
}

const fetchReviews = async () => {
  reviewsLoading.value = true
  try {
    const response = await api.get('/admin/upload-reviews', {
      params: {
        search: reviewFilters.search || undefined,
        status: reviewFilters.status || undefined,
        risk_level: reviewFilters.risk_level || undefined,
        page: reviewPagination.page,
        page_size: reviewPagination.pageSize,
      },
    })
    const payload = response.data.data || {}
    reviewRecords.value = payload.items || []
    reviewPagination.total = Number(payload.total || 0)
    reviewPagination.page = Number(payload.page || reviewPagination.page)
    reviewPagination.pageSize = Number(payload.page_size || reviewPagination.pageSize)

    const maxPage = Math.max(1, Math.ceil(reviewPagination.total / reviewPagination.pageSize))
    if (reviewPagination.page > maxPage) {
      reviewPagination.page = maxPage
      await fetchReviews()
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '待复核记录获取失败')
  } finally {
    reviewsLoading.value = false
  }
}

const refreshAll = async () => {
  try {
    await Promise.all([fetchOverview(), fetchUsers(), fetchRumors(), fetchReviews()])
    ElMessage.success('后台数据已刷新')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '刷新失败')
  }
}

const handleUserSelectionChange = (selection) => {
  selectedUserIds.value = selection.map((item) => item.user_id)
}

const handleRumorSelectionChange = (selection) => {
  selectedRumorIds.value = selection.map((item) => item.rumor_id)
}

const resetUserFilters = () => {
  userFilters.search = ''
  userFilters.role = ''
  userFilters.status = ''
  userPagination.page = 1
  fetchUsers()
}

const applyUserFilters = () => {
  userPagination.page = 1
  fetchUsers()
}

const resetRumorFilters = () => {
  rumorFilters.search = ''
  rumorFilters.source_type = ''
  rumorFilters.status = ''
  rumorFilters.source_name = ''
  rumorPagination.page = 1
  fetchRumors()
}

const applyRumorFilters = () => {
  rumorPagination.page = 1
  fetchRumors()
}

const resetReviewFilters = () => {
  reviewFilters.search = ''
  reviewFilters.status = 'all'
  reviewFilters.risk_level = ''
  reviewPagination.page = 1
  fetchReviews()
}

const applyReviewFilters = () => {
  reviewPagination.page = 1
  fetchReviews()
}

const handleUserPageChange = (page) => {
  userPagination.page = page
  fetchUsers()
}

const handleUserPageSizeChange = (pageSize) => {
  userPagination.pageSize = pageSize
  userPagination.page = 1
  fetchUsers()
}

const handleRumorPageChange = (page) => {
  rumorPagination.page = page
  fetchRumors()
}

const handleRumorPageSizeChange = (pageSize) => {
  rumorPagination.pageSize = pageSize
  rumorPagination.page = 1
  fetchRumors()
}

const handleReviewPageChange = (page) => {
  reviewPagination.page = page
  fetchReviews()
}

const handleReviewPageSizeChange = (pageSize) => {
  reviewPagination.pageSize = pageSize
  reviewPagination.page = 1
  fetchReviews()
}

const saveUser = async (row) => {
  try {
    const response = await api.patch(`/admin/users/${row.user_id}`, {
      role: row.role,
      status: row.status,
    })

    Object.assign(row, response.data.data)
    await fetchOverview()
    ElMessage.success('用户信息已更新')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '用户信息更新失败')
    fetchUsers()
  }
}

const deleteUsers = async (userIds) => {
  if (!userIds.length) {
    ElMessage.warning('请先选择要删除的用户')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认删除这 ${userIds.length} 个用户吗？此操作会同步删除其上传记录，无法撤销。`,
      '批量删除用户',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  deleteUsersLoading.value = true
  try {
    const response = await api.delete('/admin/users', {
      data: { user_ids: userIds },
      timeout: 30000,
    })
    await refreshAll()
    ElMessage.success(`已删除 ${response.data.data.deleted_count} 个用户`)
  } catch (error) {
    ElMessage.error(extractErrorPayload(error, '批量删除失败').message)
  } finally {
    deleteUsersLoading.value = false
  }
}

const uploadUsersWorkbook = async ({ file, onSuccess, onError }) => {
  if (!file.name.toLowerCase().endsWith('.xlsx')) {
    ElMessage.error('仅支持导入 .xlsx 格式文件')
    onError?.(new Error('invalid-file-type'))
    return
  }

  importUsersLoading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post('/admin/users/import', formData, {
      timeout: 120000,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })

    await refreshAll()
    await ElMessageBox.alert(
      buildImportSummaryHtml(response.data.data, '导入完成'),
      'Excel 导入结果',
      {
        dangerouslyUseHTMLString: true,
        confirmButtonText: '知道了',
      },
    )
    onSuccess?.(response.data)
  } catch (error) {
    const payload = extractErrorPayload(error, 'Excel 导入失败')
    if ((payload.errors || []).length > 0 || payload.summary) {
      await ElMessageBox.alert(
        buildImportSummaryHtml(payload, payload.message || '导入失败'),
        'Excel 导入失败',
        {
          dangerouslyUseHTMLString: true,
          confirmButtonText: '关闭',
        },
      )
    } else {
      ElMessage.error(payload.message)
    }
    onError?.(error)
  } finally {
    importUsersLoading.value = false
  }
}

const exportUsers = async () => {
  exportUsersLoading.value = true
  try {
    const response = await api.get('/admin/users/export', {
      params: {
        search: userFilters.search || undefined,
        role: userFilters.role || undefined,
        status: userFilters.status || undefined,
      },
      responseType: 'blob',
      timeout: 120000,
    })
    downloadBlobResponse(response, 'users_export.xlsx')
    ElMessage.success('用户数据导出成功')
  } catch {
    ElMessage.error('用户数据导出失败')
  } finally {
    exportUsersLoading.value = false
  }
}

const downloadImportTemplate = async () => {
  try {
    const response = await api.get('/admin/users/import-template', {
      responseType: 'blob',
      timeout: 60000,
    })
    downloadBlobResponse(response, 'users_import_template.xlsx')
    ElMessage.success('导入模板已下载')
  } catch {
    ElMessage.error('导入模板下载失败')
  }
}

const openCreateRumorDialog = () => {
  rumorDialogMode.value = 'create'
  resetRumorForm()
  rumorDialogVisible.value = true
}

const openRumorDetail = (row) => {
  activeRumorDetail.value = row
  rumorDetailVisible.value = true
}

const openEditRumorDialog = (row) => {
  rumorDialogMode.value = 'edit'
  Object.assign(rumorForm, {
    rumor_id: row.rumor_id,
    title: row.title || '',
    content: row.content || '',
    claim_text: row.claim_text || '',
    truth_text: row.truth_text || '',
    raw_content: row.raw_content || '',
    source_name: row.raw_source_name || row.source_name || '',
    article_id: row.article_id || '',
    article_url: row.article_url || '',
    publish_time: row.raw_publish_time || row.publish_time || '',
    label: row.label ?? 1,
    status: row.status || 'pass',
    source_type: row.source_type || 'system',
  })
  rumorDialogVisible.value = true
}

const submitRumorForm = async () => {
  saveRumorLoading.value = true
  try {
    const payload = normalizeRumorPayload(rumorForm)
    let response
    if (rumorDialogMode.value === 'create') {
      response = await api.post('/admin/rumors', payload, { timeout: 60000 })
    } else {
      response = await api.patch(`/admin/rumors/${rumorForm.rumor_id}`, payload, { timeout: 60000 })
    }

    rumorDialogVisible.value = false
    resetRumorForm()
    await Promise.all([fetchRumors(), fetchOverview()])
    ElMessage.success(response.data.message || '谣言数据已保存')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '谣言保存失败')
  } finally {
    saveRumorLoading.value = false
  }
}

const deleteRumors = async (rumorIds) => {
  if (!rumorIds.length) {
    ElMessage.warning('请先选择要删除的谣言')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认删除这 ${rumorIds.length} 条谣言吗？该操作会影响主谣言库检索结果，无法撤销。`,
      '批量删除谣言',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  deleteRumorsLoading.value = true
  try {
    const response = await api.delete('/admin/rumors', {
      data: { rumor_ids: rumorIds },
      timeout: 30000,
    })
    await Promise.all([fetchRumors(), fetchOverview()])
    ElMessage.success(`已删除 ${response.data.data.deleted_count} 条谣言`)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '删除谣言失败')
  } finally {
    deleteRumorsLoading.value = false
  }
}

const importPiyaoRumors = async () => {
  importRumorsLoading.value = true
  try {
    const response = await api.post('/admin/rumors/import-piyao', {}, { timeout: 120000 })
    await Promise.all([fetchRumors(), fetchOverview()])
    await ElMessageBox.alert(
      buildImportSummaryHtml(response.data.data, '平台谣言导入完成'),
      '平台数据导入结果',
      {
        dangerouslyUseHTMLString: true,
        confirmButtonText: '知道了',
      },
    )
  } catch (error) {
    const payload = extractErrorPayload(error, '平台谣言导入失败')
    ElMessage.error(payload.message)
  } finally {
    importRumorsLoading.value = false
  }
}

const openReviewDetail = (row) => {
  activeReviewDetail.value = row
  reviewDetailVisible.value = true
  reviewRumorSearch.value = row.candidate_rumor?.title || reviewSuggestedTitle(row) || ''
  reviewRumorSearchResults.value = []
  reviewActionReason.value = row.merge_reason || ''
}

const replaceReviewRecord = (nextRecord) => {
  reviewRecords.value = reviewRecords.value.map((item) => (
    item.upload_id === nextRecord.upload_id ? nextRecord : item
  ))
  if (activeReviewDetail.value?.upload_id === nextRecord.upload_id) {
    activeReviewDetail.value = nextRecord
  }
}

const submitReviewAction = async (row, payload) => {
  reviewActionLoading.value = true
  reviewActionTargetId.value = row.upload_id
  try {
    const response = await api.patch(`/admin/upload-reviews/${row.upload_id}`, payload, { timeout: 60000 })
    replaceReviewRecord(response.data.data)
    await Promise.all([fetchOverview(), fetchRumors(), fetchReviews()])
    if (activeReviewDetail.value?.upload_id === row.upload_id) {
      activeReviewDetail.value = response.data.data
    }
    ElMessage.success(response.data.message || '审核操作已完成')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '审核操作失败')
  } finally {
    reviewActionLoading.value = false
    reviewActionTargetId.value = null
  }
}

const quickMergeReview = async (row) => {
  await submitReviewAction(row, {
    action: 'merge',
    rumor_id: row.review_target_rumor_id,
  })
}

const markReviewInvalid = async (row) => {
  try {
    await ElMessageBox.confirm(
      '确认将这条记录标记为无效吗？它会保留在历史中，但不会并入主谣言库。',
      '标记无效',
      {
        type: 'warning',
        confirmButtonText: '确认',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  await submitReviewAction(row, {
    action: 'invalid',
    reason: reviewActionReason.value || row.merge_reason || undefined,
  })
}

const seedReviewRumorSearch = () => {
  reviewRumorSearch.value = reviewSuggestedTitle(activeReviewDetail.value)
  searchReviewRumors()
}

const searchReviewRumors = async () => {
  const keyword = reviewRumorSearch.value.trim()
  if (!keyword) {
    reviewRumorSearchResults.value = []
    ElMessage.warning('请先输入关键词后再搜索主谣言')
    return
  }

  reviewRumorSearchLoading.value = true
  try {
    const response = await api.get('/admin/rumors', {
      params: {
        search: keyword,
        page: 1,
        page_size: 6,
      },
      timeout: 60000,
    })
    reviewRumorSearchResults.value = response.data.data?.items || []
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '主谣言搜索失败')
  } finally {
    reviewRumorSearchLoading.value = false
  }
}

onMounted(() => {
  refreshAll()
})
</script>

<style scoped>
.admin-page {
  padding: 24px;
  display: grid;
  gap: 20px;
}

.admin-top,
.mini-card,
.admin-tabs {
  padding: 24px;
  border-radius: 28px;
}

.admin-top {
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

.admin-top h1,
.table-head h2 {
  margin: 14px 0 8px;
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1.08;
  letter-spacing: -0.04em;
  color: var(--ink-strong);
}

.admin-top p {
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
  grid-template-columns: repeat(6, minmax(0, 1fr));
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

.admin-tabs :deep(.el-tabs__header) {
  margin-bottom: 22px;
}

.review-tab-label {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.tab-inline-action {
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.92);
  color: var(--ink-main);
  padding: 8px 12px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 12px;
  line-height: 1;
  transition: 0.2s ease;
}

.tab-inline-action:hover {
  border-color: rgba(15, 123, 255, 0.24);
  color: var(--brand-deep);
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
  grid-template-columns: minmax(220px, 1fr) 180px 180px;
  gap: 12px;
}

.rumor-toolbar-row {
  grid-template-columns: minmax(220px, 1fr) 180px 180px 200px;
}

.review-toolbar-row {
  grid-template-columns: minmax(260px, 1fr) 180px 180px;
}

.toolbar-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.toolbar :deep(.el-input__wrapper),
.toolbar :deep(.el-select__wrapper) {
  min-height: 44px;
  border-radius: 14px;
  box-shadow: none;
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.rumor-brief-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.review-brief-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.brief-card {
  padding: 18px 20px;
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(15, 123, 255, 0.12), transparent 34%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 251, 255, 0.96));
}

.brief-card span {
  color: var(--ink-soft);
  font-size: 13px;
}

.brief-card strong {
  display: block;
  margin: 12px 0 10px;
  font-size: 30px;
  color: var(--ink-strong);
}

.brief-card p {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.7;
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

.review-risk-cell {
  display: grid;
  gap: 8px;
}

.review-risk-cell span {
  color: var(--ink-soft);
  font-size: 12px;
}

.drawer-head h2 {
  margin: 14px 0 8px;
  font-size: 28px;
  line-height: 1.18;
  color: var(--ink-strong);
}

.drawer-head p {
  margin: 0;
  color: var(--ink-soft);
}

.drawer-body {
  display: grid;
  gap: 14px;
}

.drawer-section {
  padding: 18px;
  border-radius: 22px;
}

.drawer-section-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.drawer-section-head span {
  color: var(--ink-soft);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.drawer-section-head a {
  color: var(--brand-deep);
  text-decoration: none;
}

.detail-label {
  display: block;
  margin-bottom: 10px;
  font-size: 12px;
  color: var(--ink-soft);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.drawer-section p,
.drawer-section a {
  margin: 0;
  line-height: 1.8;
  color: var(--ink-main);
  word-break: break-all;
}

.long-text {
  white-space: pre-wrap;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.meta-grid label {
  display: block;
  margin-bottom: 8px;
  color: var(--ink-soft);
  font-size: 12px;
}

.review-meta-grid label,
.review-binding-card label {
  display: block;
  margin-bottom: 8px;
  color: var(--ink-soft);
  font-size: 12px;
}

.review-binding-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.review-binding-card {
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(248, 250, 252, 0.92);
}

.review-binding-card strong {
  display: block;
  margin-bottom: 8px;
  color: var(--ink-strong);
  line-height: 1.6;
}

.review-binding-card p {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.7;
}

.review-candidate-list,
.review-search-results {
  display: grid;
  gap: 12px;
}

.review-candidate-card,
.review-search-card {
  display: grid;
  gap: 10px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background:
    radial-gradient(circle at top right, rgba(15, 123, 255, 0.08), transparent 34%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 250, 255, 0.96));
}

.review-candidate-meta {
  display: grid;
  gap: 6px;
}

.review-candidate-meta strong {
  color: var(--ink-strong);
  line-height: 1.6;
}

.review-candidate-meta span {
  color: var(--ink-soft);
  font-size: 12px;
}

.review-candidate-card p,
.review-search-card p {
  margin: 0;
  color: var(--ink-main);
  line-height: 1.7;
}

.review-candidate-actions,
.review-footer-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.review-candidate-actions span {
  color: var(--ink-soft);
  font-size: 12px;
}

.review-footer-actions {
  margin-top: 14px;
}

.dialog-shell {
  display: grid;
  gap: 16px;
}

.dialog-panel {
  padding: 18px;
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(246, 249, 253, 0.88), rgba(255, 255, 255, 0.98));
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.panel-headline {
  margin-bottom: 14px;
}

.panel-headline p {
  margin: 12px 0 0;
  color: var(--ink-soft);
  line-height: 1.7;
}

.dialog-grid {
  display: grid;
  gap: 14px;
}

.dialog-grid.double-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.dialog-shell :deep(.el-input__wrapper),
.dialog-shell :deep(.el-select__wrapper),
.dialog-shell :deep(.el-textarea__inner) {
  border-radius: 16px;
  box-shadow: none;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 1280px) {
  .mini-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .rumor-brief-grid,
  .review-brief-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1080px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-row,
  .rumor-toolbar-row,
  .review-toolbar-row,
  .dialog-grid.double-grid,
  .meta-grid,
  .review-binding-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .admin-page {
    padding: 14px;
  }

  .admin-top,
  .mini-card,
  .admin-tabs {
    padding: 18px;
    border-radius: 22px;
  }

  .admin-top,
  .top-actions,
  .table-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .mini-grid {
    grid-template-columns: 1fr;
  }
}
</style>
