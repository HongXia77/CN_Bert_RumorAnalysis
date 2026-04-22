<template>
  <section class="geo-panel surface-card">
    <header class="geo-top">
      <div>
        <span class="section-chip">Regional Signal</span>
        <h2>地区热度与谣言传播画像</h2>
        <p>点击全国地图可下钻到省级，再点击市级区域查看当地用户规模、上传热度与高频谣言。</p>
      </div>

      <div class="geo-actions">
        <el-tag effect="dark" type="primary" round>{{ detail.scope.display_name }}</el-tag>
        <button
          v-if="currentProvince"
          class="ghost-btn"
          @click="resetToNational"
        >
          返回全国
        </button>
        <button
          v-if="currentCity"
          class="ghost-btn"
          @click="clearSelectedCity"
        >
          返回省内
        </button>
      </div>
    </header>

    <div class="geo-kpis">
      <article v-for="item in overviewCards" :key="item.title" class="geo-kpi-card">
        <span>{{ item.title }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.description }}</small>
      </article>
    </div>

    <div class="geo-body">
      <article class="map-card">
        <div class="map-head">
          <div>
            <span class="section-chip ghost">Map Drilldown</span>
            <h3>{{ currentProvince ? `${currentProvince} 地图` : '全国地图' }}</h3>
          </div>
          <div class="map-crumb">
            <button class="crumb-btn" :class="{ active: !currentProvince }" @click="resetToNational">全国</button>
            <button
              v-if="currentProvince"
              class="crumb-btn"
              :class="{ active: currentProvince && !currentCity }"
              @click="clearSelectedCity"
            >
              {{ currentProvince }}
            </button>
            <span v-if="currentCity" class="crumb-current">{{ currentCity }}</span>
          </div>
        </div>

        <div class="map-stage">
          <div ref="mapRef" class="map-canvas" :class="{ 'is-loading': loadingMap }"></div>
          <div v-if="loadingMap" class="map-loading">
            <el-skeleton animated :rows="6" />
          </div>
        </div>

        <p class="map-tip">
          当前以“上传谣言数”着色显示，颜色越深表示该地区用户上传与传播热度越高。
        </p>
      </article>

      <aside class="detail-card">
        <div class="detail-head">
          <div>
            <span class="section-chip ghost">Region Detail</span>
            <h3>{{ detail.scope.display_name }}</h3>
          </div>
          <span class="detail-time">
            最近上传 {{ formatTime(detail.stats.latest_upload_time) }}
          </span>
        </div>

        <div class="detail-stats">
          <article>
            <span>注册用户</span>
            <strong>{{ detail.stats.user_count }}</strong>
          </article>
          <article>
            <span>上传总量</span>
            <strong>{{ detail.stats.upload_count }}</strong>
          </article>
          <article>
            <span>关联谣言</span>
            <strong>{{ detail.stats.rumor_count }}</strong>
          </article>
        </div>

        <div class="risk-stack">
          <div v-for="item in riskCards" :key="item.label" class="risk-row">
            <div>
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
            <el-progress
              :percentage="item.percentage"
              :stroke-width="10"
              :status="item.status"
            />
          </div>
        </div>

        <section class="insight-block">
          <div class="block-head">
            <h4>{{ currentProvince && !currentCity ? (isDistrictLevelProvince(currentProvince) ? '市辖区县热度' : '省内城市热度') : '地区高频谣言' }}</h4>
            <small>{{ currentProvince && !currentCity ? `点击${isDistrictLevelProvince(currentProvince) ? '区县' : '城市'}可继续查看详情` : '按上传次数排序' }}</small>
          </div>

          <div v-if="currentProvince && !currentCity" class="ranking-list">
            <button
              v-for="item in detail.cities.slice(0, 8)"
              :key="item.name"
              class="rank-item"
              @click="inspectCity(getDisplayRegionName(item.name))"
            >
              <div>
                <strong>{{ getDisplayRegionName(item.name) }}</strong>
                <small>{{ item.user_count }} 位用户 · {{ item.rumor_count }} 条谣言</small>
              </div>
              <span>{{ item.upload_count }}</span>
            </button>
          </div>
          <div v-else class="rumor-list">
            <article v-for="item in detail.top_rumors" :key="item.content" class="rumor-item">
              <strong>{{ item.preview }}</strong>
              <div>
                <span>{{ item.upload_count }} 次提及</span>
                <small>{{ formatTime(item.latest_upload_time) }}</small>
              </div>
            </article>
            <el-empty
              v-if="detail.top_rumors.length === 0"
              description="当前区域还没有足够的上传记录。"
            />
          </div>
        </section>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

import api from '@/api/client'
import { isDistrictLevelProvince, trimRegionSuffix } from '@/constants/regions'

const PROVINCE_SHORT_NAME_MAP = {
  北京市: '北京',
  天津市: '天津',
  上海市: '上海',
  重庆市: '重庆',
  河北省: '河北',
  山西省: '山西',
  辽宁省: '辽宁',
  吉林省: '吉林',
  黑龙江省: '黑龙江',
  江苏省: '江苏',
  浙江省: '浙江',
  安徽省: '安徽',
  福建省: '福建',
  江西省: '江西',
  山东省: '山东',
  河南省: '河南',
  湖北省: '湖北',
  湖南省: '湖南',
  广东省: '广东',
  海南省: '海南',
  四川省: '四川',
  贵州省: '贵州',
  云南省: '云南',
  陕西省: '陕西',
  甘肃省: '甘肃',
  青海省: '青海',
  台湾省: '台湾',
  内蒙古自治区: '内蒙古',
  广西壮族自治区: '广西',
  西藏自治区: '西藏',
  宁夏回族自治区: '宁夏',
  新疆维吾尔自治区: '新疆',
  香港特别行政区: '香港',
  澳门特别行政区: '澳门',
}

const PROVINCE_FULL_NAME_MAP = Object.fromEntries(
  Object.entries(PROVINCE_SHORT_NAME_MAP).map(([fullName, shortName]) => [shortName, fullName]),
)

const mapRef = ref(null)
const loadingMap = ref(true)
const currentProvince = ref('')
const currentProvinceCode = ref('100000')
const currentCity = ref('')
const currentMapGeo = ref(null)

const mapMeta = ref([])
const overview = ref({
  summary: {
    total_users: 0,
    total_uploads: 0,
    total_rumors: 0,
    covered_provinces: 0,
    covered_cities: 0,
    high_risk_uploads: 0,
  },
  province_stats: [],
  top_rumors: [],
})
const detail = ref({
  scope: { display_name: '全国地区画像', level: 'national' },
  stats: {
    user_count: 0,
    upload_count: 0,
    rumor_count: 0,
    high_risk_count: 0,
    medium_risk_count: 0,
    low_risk_count: 0,
    latest_upload_time: null,
  },
  cities: [],
  top_rumors: [],
})

let mapChart = null

const provinceMetaMap = computed(() => {
  const map = new Map()
  mapMeta.value.forEach((item) => {
    map.set(item.name, item)
    map.set(toMapProvinceName(item.name), item)
  })
  return map
})

const toMapProvinceName = (provinceName) => {
  if (!provinceName) {
    return ''
  }
  return PROVINCE_SHORT_NAME_MAP[provinceName] || provinceName
}

const toCanonicalProvinceName = (provinceName) => {
  if (!provinceName) {
    return ''
  }
  return PROVINCE_FULL_NAME_MAP[provinceName] || provinceName
}

const buildNameCandidates = (value) => {
  const normalized = String(value ?? '').trim()
  if (!normalized) {
    return []
  }

  const candidates = new Set([normalized])
  const strippedName = trimRegionSuffix(normalized)
  if (strippedName) {
    candidates.add(strippedName)
  }
  return [...candidates]
}

const buildFeatureCandidates = (feature) => {
  const properties = feature?.properties || {}
  const candidates = new Set()

  buildNameCandidates(properties.name).forEach((item) => candidates.add(item))
  buildNameCandidates(properties.fullname).forEach((item) => candidates.add(item))

  return [...candidates]
}

const findMatchedRegionStat = (stats, feature) => {
  const featureCandidates = buildFeatureCandidates(feature)
  if (featureCandidates.length === 0) {
    return null
  }

  return stats.find((item) => {
    const itemCandidates = buildNameCandidates(item?.name)
    return itemCandidates.some((candidate) => featureCandidates.includes(candidate))
  }) || null
}

const getDisplayRegionName = (regionName) => {
  const normalizedName = String(regionName ?? '').trim()
  if (!normalizedName || !currentMapGeo.value?.features?.length) {
    return normalizedName
  }

  const matchedFeature = currentMapGeo.value.features.find((feature) => {
    const featureCandidates = buildFeatureCandidates(feature)
    return buildNameCandidates(normalizedName).some((candidate) => featureCandidates.includes(candidate))
  })

  return matchedFeature?.properties?.fullname || matchedFeature?.properties?.name || normalizedName
}

const overviewCards = computed(() => [
  {
    title: '覆盖省份',
    value: `${overview.value.summary.covered_provinces} 个`,
    description: '已有注册用户分布的省级地区',
  },
  {
    title: '覆盖城市',
    value: `${overview.value.summary.covered_cities} 个`,
    description: '已有注册用户分布的城市数量',
  },
  {
    title: '上传总量',
    value: `${overview.value.summary.total_uploads} 条`,
    description: '所有地区用户累计上传的识别文本',
  },
  {
    title: '高风险记录',
    value: `${overview.value.summary.high_risk_uploads} 条`,
    description: '疑似谣言概率较高的上传记录',
  },
])

const riskCards = computed(() => {
  const total = Math.max(detail.value.stats.upload_count || 0, 1)
  return [
    {
      label: '高风险',
      value: detail.value.stats.high_risk_count || 0,
      percentage: Number((((detail.value.stats.high_risk_count || 0) / total) * 100).toFixed(1)),
      status: 'exception',
    },
    {
      label: '需复核',
      value: detail.value.stats.medium_risk_count || 0,
      percentage: Number((((detail.value.stats.medium_risk_count || 0) / total) * 100).toFixed(1)),
      status: 'warning',
    },
    {
      label: '较稳定',
      value: detail.value.stats.low_risk_count || 0,
      percentage: Number((((detail.value.stats.low_risk_count || 0) / total) * 100).toFixed(1)),
      status: 'success',
    },
  ]
})

const currentMapCode = computed(() => currentProvinceCode.value || '100000')
const currentMapName = computed(() => `region-${currentMapCode.value.replace(/\//g, '-')}`)

const formatTime = (value) => {
  if (!value) {
    return '--'
  }
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

const buildMapSeriesData = () => {
  const geoFeatures = currentMapGeo.value?.features || []
  if (!geoFeatures.length) {
    return []
  }

  if (!currentProvince.value) {
    const provinceStats = overview.value.province_stats || []
    return geoFeatures.map((feature) => {
      const matchedStat = findMatchedRegionStat(provinceStats, feature)
      const properties = feature.properties || {}
      const canonicalName = matchedStat?.name || toCanonicalProvinceName(properties.fullname || properties.name)

      return {
        name: properties.name || toMapProvinceName(canonicalName),
        value: matchedStat?.upload_count || 0,
        user_count: matchedStat?.user_count || 0,
        rumor_count: matchedStat?.rumor_count || 0,
        canonical_name: canonicalName,
        region_code: properties.filename || properties.code || '',
      }
    })
  }

  const cityStats = detail.value.cities || []
  return geoFeatures.map((feature) => {
    const matchedStat = findMatchedRegionStat(cityStats, feature)
    const properties = feature.properties || {}

    return {
      name: properties.name || matchedStat?.name || '',
      value: matchedStat?.upload_count || 0,
      user_count: matchedStat?.user_count || 0,
      rumor_count: matchedStat?.rumor_count || 0,
      canonical_name: matchedStat?.name || properties.fullname || properties.name || '',
      region_code: properties.filename || properties.code || '',
    }
  })
}

const renderMap = async () => {
  await nextTick()
  if (!mapRef.value || !currentMapGeo.value) {
    return
  }

  if (mapChart && mapChart.getDom() !== mapRef.value) {
    mapChart.dispose()
    mapChart = null
  }

  if (!mapChart) {
    mapChart = echarts.init(mapRef.value)
    mapChart.on('click', async (params) => {
      const regionPayload = params.data || {}
      if (!currentProvince.value) {
        await drilldownToProvince(regionPayload.canonical_name || params.name, regionPayload.region_code)
        return
      }

      const targetCity = regionPayload.canonical_name || params.name
      await inspectCity(targetCity)
    })
  }

  echarts.registerMap(currentMapName.value, currentMapGeo.value)

  const seriesData = buildMapSeriesData()
  const maxValue = Math.max(...seriesData.map((item) => Number(item.value) || 0), 1)

  mapChart.setOption(
    {
      tooltip: {
        trigger: 'item',
        formatter: (params) => {
          const data = params.data || {}
          return [
            `<strong>${params.name}</strong>`,
            `上传谣言数：${data.value || 0}`,
            `注册用户：${data.user_count || 0}`,
            `关联谣言：${data.rumor_count || 0}`,
          ].join('<br/>')
        },
      },
      visualMap: {
        min: 0,
        max: maxValue,
        left: 10,
        bottom: 6,
        text: ['热度高', '热度低'],
        orient: 'horizontal',
        calculable: true,
        itemWidth: 100,
        inRange: {
          color: ['#dbeafe', '#60a5fa', '#2563eb', '#1d4ed8'],
        },
        textStyle: {
          color: '#475569',
        },
      },
      series: [
        {
          type: 'map',
          map: currentMapName.value,
          roam: true,
          zoom: currentProvince.value ? 1.05 : 1,
          label: {
            show: true,
            color: '#1e293b',
            fontSize: currentProvince.value ? 10 : 11,
          },
          emphasis: {
            label: {
              color: '#0f172a',
            },
            itemStyle: {
              areaColor: '#fb923c',
              borderColor: '#ffffff',
              borderWidth: 1.2,
            },
          },
          itemStyle: {
            borderColor: 'rgba(255, 255, 255, 0.92)',
            borderWidth: 1,
            areaColor: '#e0f2fe',
          },
          data: seriesData,
        },
      ],
    },
    { notMerge: true },
  )
  mapChart.resize()
}

const fetchOverview = async () => {
  const response = await api.get('/analytics/geo/overview')
  overview.value = response.data.data
  if (currentMapGeo.value && !loadingMap.value) {
    await renderMap()
  }
}

const fetchDetail = async (province = '', city = '') => {
  const response = await api.get('/analytics/geo/detail', {
    params: {
      province: province || undefined,
      city: city || undefined,
    },
  })
  detail.value = response.data.data
  if (currentMapGeo.value && !loadingMap.value) {
    await renderMap()
  }
}

const fetchMapMeta = async () => {
  const response = await api.get('/map-meta')
  mapMeta.value = response.data.data || []
}

const loadMapGeo = async (regionCode) => {
  loadingMap.value = true
  try {
    const response = await api.get(`/map-geo/${regionCode}`)
    currentMapGeo.value = response.data
    currentProvinceCode.value = regionCode
  } finally {
    loadingMap.value = false
  }

  await nextTick()
  await renderMap()
}

const resetToNational = async () => {
  currentProvince.value = ''
  currentCity.value = ''
  await Promise.all([
    fetchDetail(),
    loadMapGeo('100000'),
  ])
}

const drilldownToProvince = async (provinceName, regionCode = '') => {
  const normalizedProvinceName = toCanonicalProvinceName(provinceName)
  const meta = provinceMetaMap.value.get(normalizedProvinceName)
  const resolvedProvinceName = meta?.name || normalizedProvinceName
  const targetRegionCode = String(regionCode || meta?.filename || '')
  if (!targetRegionCode) {
    ElMessage.warning(`暂未找到 ${provinceName} 的地图数据`)
    return
  }

  currentProvince.value = resolvedProvinceName
  currentCity.value = ''
  await Promise.all([
    fetchDetail(currentProvince.value),
    loadMapGeo(targetRegionCode),
  ])
}

const clearSelectedCity = async () => {
  if (!currentProvince.value) {
    await resetToNational()
    return
  }

  currentCity.value = ''
  await fetchDetail(currentProvince.value)
}

const inspectCity = async (cityName) => {
  currentCity.value = cityName
  await fetchDetail(currentProvince.value, cityName)
}

const handleResize = () => {
  mapChart?.resize()
}

watch(
  () => [currentProvince.value, currentCity.value],
  async () => {
    if (currentMapGeo.value && !loadingMap.value) {
      await nextTick()
      await renderMap()
    }
  },
)

onMounted(async () => {
  try {
    await Promise.all([
      fetchOverview(),
      fetchDetail(),
      fetchMapMeta(),
      loadMapGeo('100000'),
    ])
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '地区分析数据加载失败')
  }

  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  mapChart?.dispose()
  mapChart = null
})
</script>

<style scoped>
.geo-panel {
  padding: 22px;
  border-radius: 30px;
  display: grid;
  gap: 18px;
  background:
    radial-gradient(circle at top right, rgba(37, 99, 235, 0.12), transparent 24%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(246, 249, 255, 0.96));
}

.geo-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.section-chip {
  display: inline-flex;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(15, 123, 255, 0.1);
  color: #0f5dd7;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.section-chip.ghost {
  background: rgba(148, 163, 184, 0.12);
  color: #334155;
}

.geo-top h2,
.map-head h3,
.detail-head h3 {
  margin: 12px 0 8px;
  font-size: clamp(24px, 3vw, 34px);
  line-height: 1.08;
  letter-spacing: -0.04em;
  color: #0f172a;
}

.geo-top p {
  margin: 0;
  max-width: 780px;
  color: #475569;
  line-height: 1.75;
}

.geo-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.ghost-btn,
.crumb-btn,
.rank-item {
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(255, 255, 255, 0.88);
  color: #1e293b;
  cursor: pointer;
  transition: 0.2s ease;
}

.ghost-btn {
  padding: 10px 14px;
  border-radius: 14px;
}

.ghost-btn:hover,
.crumb-btn:hover,
.rank-item:hover {
  transform: translateY(-1px);
  border-color: rgba(37, 99, 235, 0.28);
}

.geo-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.geo-kpi-card {
  padding: 16px 18px;
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(37, 99, 235, 0.08), rgba(255, 255, 255, 0.94));
  border: 1px solid rgba(37, 99, 235, 0.12);
}

.geo-kpi-card span,
.detail-stats span,
.risk-row span,
.rumor-item span,
.detail-time,
.rank-item small,
.block-head small {
  color: #64748b;
}

.geo-kpi-card strong {
  display: block;
  margin: 8px 0 4px;
  font-size: 28px;
  color: #0f172a;
}

.geo-kpi-card small {
  line-height: 1.6;
}

.geo-body {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.82fr);
  gap: 16px;
}

.map-card,
.detail-card {
  padding: 18px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.map-head,
.detail-head,
.block-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
}

.map-crumb {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.crumb-btn,
.crumb-current {
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 12px;
}

.crumb-btn.active {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: #fff;
  border-color: transparent;
}

.crumb-current {
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
}

.map-loading {
  position: absolute;
  inset: 0;
  z-index: 1;
  padding-top: 18px;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(2px);
}

.map-stage {
  position: relative;
}

.map-canvas {
  width: 100%;
  min-height: 520px;
}

.map-canvas.is-loading {
  opacity: 0.2;
  pointer-events: none;
}

.map-tip {
  margin: 12px 0 0;
  color: #64748b;
  line-height: 1.7;
}

.detail-time {
  white-space: nowrap;
  font-size: 12px;
}

.detail-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin: 16px 0;
}

.detail-stats article {
  padding: 14px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(15, 123, 255, 0.06), rgba(255, 255, 255, 0.94));
  border: 1px solid rgba(15, 123, 255, 0.08);
}

.detail-stats strong,
.risk-row strong,
.rank-item strong,
.rumor-item strong {
  display: block;
  color: #0f172a;
}

.detail-stats strong {
  margin-top: 8px;
  font-size: 22px;
}

.risk-stack {
  display: grid;
  gap: 12px;
}

.risk-row {
  display: grid;
  gap: 8px;
}

.risk-row strong {
  margin-top: 4px;
  font-size: 18px;
}

.insight-block {
  margin-top: 18px;
  display: grid;
  gap: 12px;
}

.block-head h4 {
  margin: 0 0 4px;
  color: #0f172a;
}

.ranking-list,
.rumor-list {
  display: grid;
  gap: 10px;
}

.rank-item,
.rumor-item {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
  padding: 14px 16px;
  border-radius: 18px;
}

.rank-item span {
  min-width: 44px;
  text-align: right;
  font-weight: 700;
  color: #1d4ed8;
}

.rumor-item {
  background: rgba(248, 250, 252, 0.92);
}

.rumor-item div {
  display: grid;
  gap: 4px;
  text-align: right;
  white-space: nowrap;
}

.rumor-item small {
  color: #94a3b8;
}

@media (max-width: 1180px) {
  .geo-kpis,
  .geo-body,
  .detail-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .geo-kpis,
  .geo-body,
  .detail-stats {
    grid-template-columns: 1fr;
  }

  .map-canvas {
    min-height: 420px;
  }
}

@media (max-width: 720px) {
  .geo-panel,
  .map-card,
  .detail-card {
    padding: 16px;
    border-radius: 22px;
  }

  .geo-top,
  .geo-actions,
  .map-head,
  .detail-head,
  .block-head,
  .rank-item,
  .rumor-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .rumor-item div,
  .rank-item span {
    text-align: left;
  }
}
</style>
