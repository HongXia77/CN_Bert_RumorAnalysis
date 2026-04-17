<template>
  <div class="map-wrapper">
    <div ref="mapDom" class="map-container" style="width: 800px; height: 600px;"></div>

    <Transition name="fade">
      <button
        v-show="currentMap !== 'china'"
        class="back-btn"
        @click="backToChina"
      >
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
        返回全国
      </button>
    </Transition>
  </div>
</template>

<script setup>
import { ref, shallowRef, onMounted, onBeforeUnmount } from 'vue';
import * as echarts from 'echarts';

const mapDom = ref(null);
// 🚨 必须是 shallowRef，否则卡顿到无法使用！
const chartInstance = shallowRef(null);
const currentMap = ref('china');

// 全国各省行政区划代码字典 (DataV 标准)
const adcodeMap = {
  '北京市': '110000', '天津市': '120000', '河北省': '130000', '山西省': '140000',
  '内蒙古自治区': '150000', '辽宁省': '210000', '吉林省': '220000', '黑龙江省': '230000',
  '上海市': '310000', '江苏省': '320000', '浙江省': '330000', '安徽省': '340000',
  '福建省': '350000', '江西省': '360000', '山东省': '370000', '河南省': '410000',
  '湖北省': '420000', '湖南省': '430000', '广东省': '440000', '广西壮族自治区': '450000',
  '海南省': '460000', '重庆市': '500000', '四川省': '510000', '贵州省': '520000',
  '云南省': '530000', '西藏自治区': '540000', '陕西省': '610000', '甘肃省': '620000',
  '青海省': '630000', '宁夏回族自治区': '640000', '新疆维吾尔自治区': '650000',
  '台湾省': '710000', '香港特别行政区': '810000', '澳门特别行政区': '820000'
};

/**
 * 直接从 DataV 官方 CDN 获取干净的地图数据
 */
const fetchMapData = async (mapName) => {
  let adcode = '100000'; // 默认全国

  if (mapName !== 'china') {
    adcode = adcodeMap[mapName];
    if (!adcode) {
      console.warn(`未找到 ${mapName} 的行政区划代码`);
      return null;
    }
  }

  try {
    // 调用阿里云公开 JSON，省去你自己下载一堆文件的麻烦
    const url = `https://geo.datav.aliyun.com/areas_v3/bound/${adcode}_full.json`;
    const response = await fetch(url);
    return await response.json();
  } catch (error) {
    console.error('获取地图数据失败:', error);
    return null;
  }
};

const getMapOption = (mapName) => {
  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(0, 15, 36, 0.8)',
      borderColor: '#1790cf',
      textStyle: { color: '#fff' },
      formatter: '{b}'
    },
    series: [{
      type: 'map',
      map: mapName,
      roam: false,
      zoom: 1.1,
      label: {
        show: true,
        color: '#fff',
        fontSize: 10 // 字体调小一点，避免拥挤
      },
      itemStyle: {
        areaColor: '#0a1d3a',
        borderColor: '#1790cf',
        borderWidth: 1,
      },
      emphasis: {
        label: { color: '#fff' },
        itemStyle: { areaColor: '#1661ab' }
      },
      // 开启平滑过渡动画
      animationDurationUpdate: 800,
      animationEasingUpdate: 'cubicInOut'
    }]
  };
};

const renderMap = async (mapName) => {
  if (!chartInstance.value) return;

  // 开启加载动画，提升体验
  chartInstance.value.showLoading({ maskColor: 'rgba(1, 10, 23, 0.8)', textColor: '#fff' });

  const geoJson = await fetchMapData(mapName);

  chartInstance.value.hideLoading();

  if (geoJson) {
    echarts.registerMap(mapName, geoJson);
    currentMap.value = mapName;
    // 第二个参数 true 表示清除上一次的配置，防止残留
    chartInstance.value.setOption(getMapOption(mapName), true);
  }
};

const backToChina = () => {
  if (currentMap.value === 'china') return;
  renderMap('china');
};

onMounted(() => {
  chartInstance.value = echarts.init(mapDom.value);

  // 1. 先渲染全国
  renderMap('china');

  // 2. 点击省份下钻
  chartInstance.value.on('click', (params) => {
    // 只有在全国视图下才允许钻取，防止在市级地图继续瞎钻报错
    if (currentMap.value === 'china') {
      renderMap(params.name);
    }
  });

  window.addEventListener('resize', () => chartInstance.value?.resize());
});

onBeforeUnmount(() => {
  chartInstance.value?.dispose();
});
</script>

<style scoped>
.map-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 600px; /* 根据实际需求调整 */
  background: #010A17;
  overflow: hidden;
  border-radius: 8px; /* 如果需要边框圆角 */
}

.map-container {
  width: 100%;
  height: 100%;
}

.back-btn {
  position: absolute;
  top: 20px;
  left: 20px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(17, 128, 199, 0.15);
  border: 1px solid rgba(23, 144, 207, 0.5);
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  backdrop-filter: blur(8px);
  border-radius: 4px;
  transition: all 0.3s ease;
  z-index: 10; /* 确保在地图图层之上 */
}

.back-btn:hover {
  background: rgba(17, 128, 199, 0.4);
  border-color: #1790cf;
  box-shadow: 0 0 10px rgba(23, 144, 207, 0.4);
}

.icon {
  width: 16px;
  height: 16px;
}

/* Vue 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}
</style>
