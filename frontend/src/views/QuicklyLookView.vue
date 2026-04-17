<template>
  <div class="rumor-nav-container">
    <div class="page-header">
      <h1 class="title">速看！辟谣</h1>
      <p class="desc">汇集全网权威声音，粉碎不实谣言。点击卡片快速查看最新辟谣动态。</p>
    </div>

    <div class="section-block">
      <div class="section-header">
        <el-icon class="header-icon" color="#409EFF"><InfoFilled /></el-icon>
        <h2>权威官方</h2>
        <el-tag size="small" type="primary" effect="light" class="header-tag">国家/机构认证</el-tag>
      </div>

      <el-row :gutter="24">
        <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="item in officialList" :key="item.id" class="card-col">
          <el-card class="nav-card" shadow="hover" @click="handleCardClick(item)">
            <div class="card-content">
              <el-avatar :size="50" :src="item.avatar" class="card-avatar">
                {{ item.name.charAt(0) }}
              </el-avatar>
              <div class="card-info">
                <h3 class="name">{{ item.name }}</h3>
                <p class="slogan">{{ item.slogan }}</p>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <div class="section-block">
      <div class="section-header">
        <el-icon class="header-icon" color="#F56C6C"><Star /></el-icon>
        <h2>精选 UP 主</h2>
        <el-tag size="small" type="danger" effect="light" class="header-tag">硬核科普优质创作者</el-tag>
      </div>

      <el-row :gutter="24">
        <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="up in creatorList" :key="up.id" class="card-col">
          <el-card class="nav-card creator-card" shadow="hover" @click="handleCardClick(up)">
            <div class="card-content">
              <el-avatar :size="50" :src="up.avatar" class="card-avatar">
                {{ up.name.charAt(0) }}
              </el-avatar>
              <div class="card-info">
                <div class="name-row">
                  <h3 class="name">{{ up.name }}</h3>
                  <el-tag size="small" :type="up.platformType" class="platform-tag">{{ up.platform }}</el-tag>
                </div>
                <p class="slogan">{{ up.fans }} 关注 · {{ up.domain }}</p>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>

<!--  -->
  <el-drawer
      v-model="drawerVisible"
      :title="activeItem?.name || '详情'"
      size="40%"
      destroy-on-close
    >
      <div class="drawer-header-info" v-if="activeItem">
        <el-avatar :size="64" :src="activeItem.avatar" class="drawer-avatar">
          {{ activeItem.name.charAt(0) }}
        </el-avatar>
        <div class="drawer-meta">
          <h2 class="drawer-title">{{ activeItem.name }}</h2>
          <p class="drawer-slogan">{{ activeItem.slogan || (activeItem.fans + ' 关注 · ' + activeItem.domain) }}</p>
          <div class="drawer-tags">
            <el-tag size="small" type="success" effect="plain" v-if="activeItem.platform">{{ activeItem.platform }} 认证</el-tag>
            <el-tag size="small" type="primary" effect="plain" v-else>官方机构认证</el-tag>
          </div>
        </div>
      </div>

      <el-divider />

      <div class="drawer-body">
        <h3 class="body-title">最新辟谣动态</h3>

        <div class="article-list">
          <div class="article-item" v-for="i in 3" :key="i">
            <div class="article-time">2026-04-1{{ i }} 14:30</div>
            <h4 class="article-title">【辟谣】关于近期网传“某地出现不明发光飞行物”的真相核实</h4>
            <p class="article-summary">近日，多名网友反映夜空中出现奇异光团。经天文台与气象部门联合核实，该现象实为……</p>
            <el-button link type="primary">阅读全文 <el-icon class="el-icon--right"><ArrowRight /></el-icon></el-button>
          </div>
        </div>
      </div>
    </el-drawer>


</template>

<script setup>
import { ref } from 'vue';
import { InfoFilled, Star, ArrowRight } from '@element-plus/icons-vue';

// 模拟数据：权威官方
const officialList = ref([
  { id: 1, name: '中国互联网联合辟谣平台', slogan: '中央网信办主办', avatar: '' },
  { id: 2, name: '较真辟谣平台', slogan: '腾讯全网事实查证平台', avatar: '' },
  { id: 3, name: '科学辟谣', slogan: '中国科协官方辟谣账号', avatar: '' },
  { id: 4, name: '丁香医生', slogan: '可信赖的医疗健康服务', avatar: '' },
  { id: 5, name: '上海辟谣平台', slogan: '解放日报·上观新闻', avatar: '' },
]);

// 模拟数据：精选UP主
const creatorList = ref([
  { id: 101, name: '无穷小亮的科普日常', domain: '生物与自然科普', fans: '780万', platform: 'Bilibili', platformType: 'info', avatar: '' },
  { id: 102, name: '回形针PaperClip', domain: '泛科普与硬核图解', fans: '300万', platform: 'Bilibili', platformType: 'info', avatar: '' },
  { id: 103, name: '央视新闻', domain: '社会时政热点核实', fans: '1.2亿', platform: '微博', platformType: 'warning', avatar: '' },
  { id: 104, name: '老爸评测', domain: '日用品与食品打假', fans: '2000万', platform: '抖音', platformType: 'default', avatar: '' },
]);

// 抽屉控制状态
const drawerVisible = ref(false);
const activeItem = ref(null); // 记录当前点击的卡片数据

// 修改：点击卡片时，将数据赋值给 activeItem 并打开抽屉
const handleCardClick = (item) => {
  activeItem.value = item;
  drawerVisible.value = true;

  // TODO: 如果有后端，可以在这里根据 item.id 发起请求获取最新的文章列表
  // fetchLatestDebunks(item.id)
};
</script>

<style scoped>
.rumor-nav-container {
  padding: 24px;
  background-color: #f5f7fa; /* 匹配参考图的浅灰底色，让纯白卡片凸显 */
  min-height: 100vh;
  box-sizing: border-box;
}

.page-header {
  margin-bottom: 32px;
}

.page-header .title {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px 0;
}

.page-header .desc {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

.section-block {
  margin-bottom: 40px;
}

.section-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.header-icon {
  font-size: 24px;
  margin-right: 8px;
}

.section-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.header-tag {
  margin-left: 12px;
  border-radius: 4px;
}

.card-col {
  margin-bottom: 20px;
}

/* 卡片核心样式 */
.nav-card {
  border: none;
  border-radius: 12px; /* 现代感的圆角 */
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.nav-card:hover {
  transform: translateY(-4px); /* 悬浮上移交互 */
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08) !important;
}

/* 覆盖 Element Plus 默认的 padding 以达到更紧凑的设计 */
:deep(.el-card__body) {
  padding: 20px;
}

.card-content {
  display: flex;
  align-items: center;
}

.card-avatar {
  background-color: #e4e8eb;
  color: #909399;
  flex-shrink: 0;
  font-weight: bold;
}

.card-info {
  margin-left: 16px;
  flex: 1;
  overflow: hidden;
}

.name-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.name {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  margin: 0 0 6px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.slogan {
  font-size: 13px;
  color: #909399;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.platform-tag {
  flex-shrink: 0;
  transform: scale(0.9);
  transform-origin: right center;
}

/* 抽屉内部样式 */
.drawer-header-info {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.drawer-avatar {
  background-color: #e4e8eb;
  color: #909399;
  font-size: 24px;
  font-weight: bold;
}

.drawer-meta {
  margin-left: 20px;
}

.drawer-title {
  margin: 0 0 8px 0;
  font-size: 22px;
  color: #303133;
}

.drawer-slogan {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #606266;
}

.drawer-tags {
  display: flex;
  gap: 8px;
}

/* 占位文章列表样式 */
.body-title {
  font-size: 18px;
  color: #303133;
  margin-bottom: 16px;
  border-left: 4px solid #409EFF;
  padding-left: 12px;
}

.article-item {
  padding: 16px 0;
  border-bottom: 1px solid #ebeef5;
}

.article-item:last-child {
  border-bottom: none;
}

.article-time {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.article-title {
  font-size: 16px;
  color: #303133;
  margin: 0 0 8px 0;
  line-height: 1.5;
}

.article-summary {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
  margin: 0 0 12px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
