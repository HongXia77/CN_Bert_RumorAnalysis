<template>
  <div class="login-page">
    <div class="left-section">
      <div class="brand-content">
        <div class="logo">
          <div class="logo-icon"></div>
        </div>
        <h1 class="project-title">谣言分析系统</h1>
        <p class="project-desc">智能识别 · 自动聚类 · 辟谣溯源</p>
      </div>
    </div>

    <div class="right-section">
      <div class="card-wrapper">

        <el-card
          class="card login-card"
          :class="{
            slideOut: isRegisterMode,
            'is-inactive': isRegisterMode
          }"
          shadow="hover"
          :body-style="{ padding: '30px', height: '100%', boxSizing: 'border-box', overflowY: 'auto' }"
          @click="isRegisterMode && switchToLogin()"
        >
          <div class="auth-header">
            <h2>欢迎回来</h2>
            <p>请登录您的账号</p>
          </div>

          <el-form :model="loginForm" size="large" @keyup.enter="handleLogin">
            <el-form-item :error="loginErrors.username">
              <label class="form-label">用户名/邮箱</label>
              <el-input
                v-model="loginForm.username"
                placeholder="请输入用户名或邮箱"
                @input="clearError('login')"
                clearable
              />
            </el-form-item>

            <el-form-item :error="loginErrors.password">
              <label class="form-label">密码</label>
              <el-input
                v-model="loginForm.password"
                type="password"
                placeholder="请输入密码"
                @input="clearError('login')"
                show-password
                clearable
              />
            </el-form-item>

            <div v-if="loginErrors.username || loginErrors.password" class="error-tip">
              {{ loginErrors.username || loginErrors.password }}
            </div>

            <el-form-item>
              <div class="action-row">
                <el-checkbox v-model="loginForm.remember">记住我</el-checkbox>
                <el-link type="primary" :underline="false" class="forget">忘记密码？</el-link>
              </div>
            </el-form-item>

            <el-form-item class="mt-4">
              <el-button
                type="primary"
                class="submit-btn"
                @click.stop="handleLogin"
                :loading="isLoginLoading"
                size="large"
              >
                {{ isLoginLoading ? '登录中...' : '登录' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-popover
          placement="right-start"
          :width="220"
          trigger="hover"
          :show-after="150"
          :hide-after="100"
          :disabled="isRegisterMode"
          :teleported="false"
          popper-class="custom-register-popover"
        >
          <template #reference>
            <el-card
              class="card lower-card"
              :class="{
                slideIn: isRegisterMode,
                'is-inactive': !isRegisterMode
              }"
              shadow="hover"
              :body-style="{ padding: '30px', height: '100%', boxSizing: 'border-box', overflowY: 'auto' }"
              @click="!isRegisterMode && switchToRegister()"
            >

              <div v-if="!isRegisterMode" class="lower-card-content teaser-content">
                <h2>还没有账号？</h2>
                <p>立即注册，加入谣言分析系统</p>
                <div class="switch-text">
                  <el-button type="primary" link class="register-link">立即注册</el-button>
                </div>
              </div>

              <div v-else class="lower-card-content full-form-content">
                <div class="register-header">
                  <div>
                    <h2 class="form-title">创建账号</h2>
                    <p class="form-subtitle">请填写您的详细信息以完成注册。</p>
                  </div>
                  <el-button plain icon="Back" @click.stop="switchToLogin" class="back-btn">
                    返回登录
                  </el-button>
                </div>

                <el-form
                  ref="registerFormRef"
                  :model="registerForm"
                  :rules="registerRules"
                  label-position="top"
                  require-asterisk-position="right"
                  @click.stop
                >
                  <el-form-item label="头像 (选填)" prop="avatar" class="avatar-item">
                    <el-upload
                      class="avatar-uploader"
                      action="/api/upload/mock"
                      :show-file-list="false"
                      :on-success="handleAvatarSuccess"
                      :before-upload="beforeAvatarUpload"
                      accept="image/png, image/jpeg"
                    >
                      <img v-if="registerForm.avatar" :src="registerForm.avatar" class="avatar" alt="预览" />
                      <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
                    </el-upload>
                  </el-form-item>

                  <div class="form-grid">
                    <el-form-item label="用户名" prop="username">
                      <el-input v-model="registerForm.username" placeholder="支持中英文字符或数字" clearable />
                    </el-form-item>

                    <el-form-item label="密码" prop="password">
                      <el-input v-model="registerForm.password" type="password" placeholder="字母/数字/特殊字符" show-password />
                    </el-form-item>

                    <el-form-item label="电子邮箱" prop="email">
                      <el-input v-model="registerForm.email" type="email" placeholder="example@domain.com" clearable />
                    </el-form-item>

                    <el-form-item label="手机号码" prop="phone">
                      <el-input v-model="registerForm.phone" placeholder="请输入11位手机号" clearable>
                        <template #prepend>+86</template>
                      </el-input>
                    </el-form-item>

                    <el-form-item label="性别" prop="gender">
                      <el-select v-model="registerForm.gender" placeholder="请选择" class="w-100">
                        <el-option label="男" value="Male" />
                        <el-option label="女" value="Female" />
                        <el-option label="未知" value="Unknown" />
                      </el-select>
                    </el-form-item>

                    <el-form-item label="生日" prop="birthday">
                      <el-date-picker v-model="registerForm.birthday" type="date" placeholder="选择日期" value-format="x" :disabled-date="disabledFutureDates" class="w-100" />
                    </el-form-item>

                    <el-form-item label="省份" prop="province">
                      <el-select v-model="registerForm.province" placeholder="请选择省份" @change="handleProvinceChange" class="w-100">
                        <el-option v-for="(cities, prov) in regionData" :key="prov" :label="prov" :value="prov" />
                      </el-select>
                    </el-form-item>

                    <el-form-item label="城市" prop="city">
                      <el-select v-model="registerForm.city" placeholder="请选择城市" :disabled="!registerForm.province" class="w-100">
                        <el-option v-for="city in availableCities" :key="city" :label="city" :value="city" />
                      </el-select>
                    </el-form-item>
                  </div>

                  <el-form-item class="submit-item mt-4">
                    <el-button type="primary" size="large" :loading="isRegisterLoading" @click.stop="handleRegister(registerFormRef)" class="submit-btn">
                      立即注册
                    </el-button>
                  </el-form-item>
                </el-form>
              </div>

            </el-card>
          </template>

          <div class="popover-inner-content">
            <div class="api-image-placeholder">
              <el-icon class="img-icon"><Picture /></el-icon>
              <span>动态图片加载区</span>
            </div>
            <div class="popover-text">
              <span class="highlight">没有账号？</span>注册一个吧！
            </div>
          </div>
        </el-popover>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { Plus, Back, Picture, Check } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted } from "vue"

// 初始化路由
const router = useRouter()

// ================= 交互状态 =================
const isRegisterMode = ref(false)

const switchToRegister = () => {
  isRegisterMode.value = true
  clearError('login')
}

const switchToLogin = () => {
  isRegisterMode.value = false
  // 返回登录时可选重置注册表单
  if (registerFormRef.value) {
    registerFormRef.value.resetFields()
  }
}

// ================= 登录逻辑 =================
const isLoginLoading = ref(false)
const loginForm = reactive({ username: '', password: '', remember: false })
const loginErrors = reactive({ username: '', password: '' })

const clearError = (type) => {
  if (type === 'login') {
    loginErrors.username = ''; loginErrors.password = ''
  }
}

const validateLoginForm = () => {
  let isValid = true
  if (!loginForm.username.trim()) { loginErrors.username = '请输入用户名或邮箱'; isValid = false }
  if (!loginForm.password) { loginErrors.password = '请输入密码'; isValid = false }
  return isValid
}

const handleLogin = async () => {
  clearError('login')
  if (!validateLoginForm()) return

  isLoginLoading.value = true

  try {
    // 1. 发送真实的 POST 请求到你的 FastAPI 后端
    const response = await axios.post('http://127.0.0.1:8000/api/user/login', {
      username: loginForm.username,
      password: loginForm.password
    })

    const resData = response.data

    // 2. 判断后端返回的自定义状态码
    if (resData.code === 200) {
      ElMessage.success('登录成功！')

      // 3. 将用户信息（包含 role 用户级别）缓存到本地，供其他页面使用
      localStorage.setItem('userInfo', JSON.stringify(resData.data))

      // (可选) 如果勾选了"记住我"，可以额外存一个标记或长时间的Token
      if (loginForm.remember) {
         localStorage.setItem('rememberUser', loginForm.username)
      }

      // 4. 根据用户级别 (role) 动态跳转页面
      if (resData.data.role === 'admin') {
        // 如果是管理员，跳转到管理后台界面 (确保你在 router/index.js 中配了此路由)
        router.push('/main')
      } else {
        // 普通用户跳转到主页
        router.push('/main')
      }
    }
  } catch (error) {
    // 捕获 FastAPI 后端抛出的 HTTPException (比如 400 错误)
    if (error.response && error.response.status === 400) {
      // 显示后端返回的具体错误信息 (如"密码错误"或"账号未激活")
      ElMessage.error(error.response.data.detail || '登录失败')
    } else {
      // 捕获网络不通等其他问题
      ElMessage.error('网络请求失败，请检查后端服务是否启动')
    }
  } finally {
    // 无论成功失败，关闭 loading 状态
    isLoginLoading.value = false
  }
}

onMounted(() => {
  const remembered = localStorage.getItem('rememberUser')
  if (remembered) {
    loginForm.username = remembered
    loginForm.remember = true
  }
})

// ================= 注册逻辑 =================
const registerFormRef = ref(null)
const isRegisterLoading = ref(false)

const registerForm = reactive({
  username: '', password: '', email: '', phone: '',
  avatar: '', gender: '', province: '', city: '', birthday: ''
})

// 地区数据 (简略展示，可自行填充完整)
// --- 模拟地区数据 ---
const regionData = {
  // 直辖市
  '北京市': ['北京市'],
  '天津市': ['天津市'],
  '上海市': ['上海市'],
  '重庆市': ['重庆市'],

  // 河北省
  '河北省': [
    '石家庄市', '唐山市', '秦皇岛市', '邯郸市', '邢台市',
    '保定市', '张家口市', '承德市', '沧州市', '廊坊市', '衡水市'
  ],

  // 山西省
  '山西省': [
    '太原市', '大同市', '阳泉市', '长治市', '晋城市',
    '朔州市', '晋中市', '运城市', '忻州市', '临汾市', '吕梁市'
  ],

  // 内蒙古自治区
  '内蒙古自治区': [
    '呼和浩特市', '包头市', '乌海市', '赤峰市', '通辽市',
    '鄂尔多斯市', '呼伦贝尔市', '巴彦淖尔市', '乌兰察布市',
    '兴安盟', '锡林郭勒盟', '阿拉善盟'
  ],

  // 辽宁省
  '辽宁省': [
    '沈阳市', '大连市', '鞍山市', '抚顺市', '本溪市',
    '丹东市', '锦州市', '营口市', '阜新市', '辽阳市',
    '盘锦市', '铁岭市', '朝阳市', '葫芦岛市'
  ],

  // 吉林省
  '吉林省': [
    '长春市', '吉林市', '四平市', '辽源市', '通化市',
    '白山市', '松原市', '白城市', '延边朝鲜族自治州'
  ],

  // 黑龙江省
  '黑龙江省': [
    '哈尔滨市', '齐齐哈尔市', '鸡西市', '鹤岗市', '双鸭山市',
    '大庆市', '伊春市', '佳木斯市', '七台河市', '牡丹江市',
    '黑河市', '绥化市', '大兴安岭地区'
  ],

  // 江苏省
  '江苏省': [
    '南京市', '无锡市', '徐州市', '常州市', '苏州市',
    '南通市', '连云港市', '淮安市', '盐城市', '扬州市',
    '镇江市', '泰州市', '宿迁市'
  ],

  // 浙江省
  '浙江省': [
    '杭州市', '宁波市', '温州市', '嘉兴市', '湖州市',
    '绍兴市', '金华市', '衢州市', '舟山市', '台州市', '丽水市'
  ],

  // 安徽省
  '安徽省': [
    '合肥市', '芜湖市', '蚌埠市', '淮南市', '马鞍山市',
    '淮北市', '铜陵市', '安庆市', '黄山市', '滁州市',
    '阜阳市', '宿州市', '六安市', '亳州市', '池州市', '宣城市'
  ],

  // 福建省
  '福建省': [
    '福州市', '厦门市', '莆田市', '三明市', '泉州市',
    '漳州市', '南平市', '龙岩市', '宁德市'
  ],

  // 江西省
  '江西省': [
    '南昌市', '景德镇市', '萍乡市', '九江市', '新余市',
    '鹰潭市', '赣州市', '吉安市', '宜春市', '抚州市', '上饶市'
  ],

  // 山东省
  '山东省': [
    '济南市', '青岛市', '淄博市', '枣庄市', '东营市',
    '烟台市', '潍坊市', '济宁市', '泰安市', '威海市',
    '日照市', '临沂市', '德州市', '聊城市', '滨州市', '菏泽市'
  ],

  // 河南省
  '河南省': [
    '郑州市', '开封市', '洛阳市', '平顶山市', '安阳市',
    '鹤壁市', '新乡市', '焦作市', '濮阳市', '许昌市',
    '漯河市', '三门峡市', '南阳市', '商丘市', '信阳市',
    '周口市', '驻马店市', '济源市'
  ],

  // 湖北省
  '湖北省': [
    '武汉市', '黄石市', '十堰市', '宜昌市', '襄阳市',
    '鄂州市', '荆门市', '孝感市', '荆州市', '黄冈市',
    '咸宁市', '随州市', '恩施土家族苗族自治州', '仙桃市',
    '潜江市', '天门市', '神农架林区'
  ],

  // 湖南省
  '湖南省': [
    '长沙市', '株洲市', '湘潭市', '衡阳市', '邵阳市',
    '岳阳市', '常德市', '张家界市', '益阳市', '郴州市',
    '永州市', '怀化市', '娄底市', '湘西土家族苗族自治州'
  ],

  // 广东省
  '广东省': [
    '广州市', '韶关市', '深圳市', '珠海市', '汕头市',
    '佛山市', '江门市', '湛江市', '茂名市', '肇庆市',
    '惠州市', '梅州市', '汕尾市', '河源市', '阳江市',
    '清远市', '东莞市', '中山市', '潮州市', '揭阳市', '云浮市'
  ],

  // 广西壮族自治区
  '广西壮族自治区': [
    '南宁市', '柳州市', '桂林市', '梧州市', '北海市',
    '防城港市', '钦州市', '贵港市', '玉林市', '百色市',
    '贺州市', '河池市', '来宾市', '崇左市'
  ],

  // 海南省
  '海南省': [
    '海口市', '三亚市', '三沙市', '儋州市',
    '五指山市', '琼海市', '文昌市', '万宁市', '东方市',
    '定安县', '屯昌县', '澄迈县', '临高县', '白沙黎族自治县',
    '昌江黎族自治县', '乐东黎族自治县', '陵水黎族自治县',
    '保亭黎族苗族自治县', '琼中黎族苗族自治县'
  ],

  // 四川省
  '四川省': [
    '成都市', '自贡市', '攀枝花市', '泸州市', '德阳市',
    '绵阳市', '广元市', '遂宁市', '内江市', '乐山市',
    '南充市', '眉山市', '宜宾市', '广安市', '达州市',
    '雅安市', '巴中市', '资阳市', '阿坝藏族羌族自治州',
    '甘孜藏族自治州', '凉山彝族自治州'
  ],

  // 贵州省
  '贵州省': [
    '贵阳市', '六盘水市', '遵义市', '安顺市', '毕节市',
    '铜仁市', '黔西南布依族苗族自治州',
    '黔东南苗族侗族自治州', '黔南布依族苗族自治州'
  ],

  // 云南省
  '云南省': [
    '昆明市', '曲靖市', '玉溪市', '保山市', '昭通市',
    '丽江市', '普洱市', '临沧市', '楚雄彝族自治州',
    '红河哈尼族彝族自治州', '文山壮族苗族自治州',
    '西双版纳傣族自治州', '大理白族自治州',
    '德宏傣族景颇族自治州', '怒江傈僳族自治州',
    '迪庆藏族自治州'
  ],

  // 西藏自治区
  '西藏自治区': [
    '拉萨市', '日喀则市', '昌都市', '林芝市', '山南市',
    '那曲市', '阿里地区'
  ],

  // 陕西省
  '陕西省': [
    '西安市', '铜川市', '宝鸡市', '咸阳市', '渭南市',
    '延安市', '汉中市', '榆林市', '安康市', '商洛市'
  ],

  // 甘肃省
  '甘肃省': [
    '兰州市', '嘉峪关市', '金昌市', '白银市', '天水市',
    '武威市', '张掖市', '平凉市', '酒泉市', '庆阳市',
    '定西市', '陇南市', '临夏回族自治州', '甘南藏族自治州'
  ],

  // 青海省
  '青海省': [
    '西宁市', '海东市', '海北藏族自治州', '黄南藏族自治州',
    '海南藏族自治州', '果洛藏族自治州', '玉树藏族自治州',
    '海西蒙古族藏族自治州'
  ],

  // 宁夏回族自治区
  '宁夏回族自治区': [
    '银川市', '石嘴山市', '吴忠市', '固原市', '中卫市'
  ],

  // 新疆维吾尔自治区
  '新疆维吾尔自治区': [
    '乌鲁木齐市', '克拉玛依市', '吐鲁番市', '哈密市',
    '昌吉回族自治州', '博尔塔拉蒙古自治州',
    '巴音郭楞蒙古自治州', '阿克苏地区',
    '克孜勒苏柯尔克孜自治州', '喀什地区', '和田地区',
    '伊犁哈萨克自治州', '塔城地区', '阿勒泰地区',
    '石河子市', '阿拉尔市', '图木舒克市', '五家渠市',
    '北屯市', '铁门关市', '双河市', '可克达拉市',
    '昆玉市', '胡杨河市', '新星市'
  ],

  // 港澳台
  '香港特别行政区': ['香港'],
  '澳门特别行政区': ['澳门'],
  '台湾省': [
    '台北市', '新北市', '桃园市', '台中市', '台南市', '高雄市',
    '基隆市', '新竹市', '嘉义市', '新竹县', '苗栗县',
    '彰化县', '南投县', '云林县', '嘉义县', '屏东县',
    '宜兰县', '花莲县', '台东县', '澎湖县'
  ]
}

const availableCities = computed(() => registerForm.province ? regionData[registerForm.province] : [])
const handleProvinceChange = () => { registerForm.city = '' }
const disabledFutureDates = (time) => time.getTime() > Date.now()

const handleAvatarSuccess = (response) => {
  // response 是后端 /upload-avatar 返回的对象
  if (response.code === 200) {
    registerForm.avatar = response.url
    ElMessage.success('头像上传成功')
  } else {
    ElMessage.error('头像上传失败')
  }
}
const beforeAvatarUpload = (rawFile) => {
  const isValidFormat = rawFile.type === 'image/jpeg' || rawFile.type === 'image/png'
  const isLt2M = rawFile.size / 1024 / 1024 < 2
  if (!isValidFormat) ElMessage.error('只能上传 JPG 或 PNG 格式!')
  if (!isLt2M) ElMessage.error('大小不能超过 2MB!')
  return isValidFormat && isLt2M
}

const validateUsername = (rule, value, callback) => {
  if (!value) callback(new Error('请输入用户名'))
  else if (!/^[\u4e00-\u9fa5a-zA-Z0-9]+$/.test(value)) callback(new Error('仅允许中英文字符或数字'))
  else callback()
}
const validatePassword = (rule, value, callback) => {
  if (!value) callback(new Error('请输入密码'))
  else if (value.length < 8) callback(new Error('长度至少为 8 位'))
  else if (!/^[a-zA-Z0-9!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]+$/.test(value)) callback(new Error('仅允许字母/数字/特殊字符'))
  else callback()
}
const validatePhone = (rule, value, callback) => {
  if (!value) callback(new Error('请输入手机号码'))
  else if (!/^1[3-9]\d{9}$/.test(value)) callback(new Error('请输入正确的手机号码'))
  else callback()
}

const registerRules = reactive({
  username: [{ required: true, validator: validateUsername, trigger: 'blur' }],
  password: [{ required: true, validator: validatePassword, trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '格式不正确', trigger: ['blur', 'change'] }],
  phone: [{ required: true, validator: validatePhone, trigger: 'blur' }],
  gender: [{ required: true, message: '请选择性别', trigger: 'change' }],
  birthday: [{ required: true, message: '请选择出生日期', trigger: 'change' }],
  province: [{ required: true, message: '请选择省份', trigger: 'change' }],
  city: [{ required: true, message: '请选择城市', trigger: 'change' }]
})

const handleRegister = async (formEl) => {
  if (!formEl) return
  await formEl.validate(async (valid) => {
    if (valid) {
      isRegisterLoading.value = true
      try {
        // 使用 FormData 处理 multipart 数据（或者直接发 JSON，因为头像已提前上传）
        const formData = new FormData()
        Object.keys(registerForm).forEach(key => {
          if (key === 'birthday') {
            formData.append('birthday_ts', registerForm.birthday)
          } else {
            formData.append(key, registerForm[key])
          }
        })

        const response = await axios.post('http://127.0.0.1:8000/api/user/register', formData)

        if (response.data.code === 200) {
          ElMessage.success('注册成功！正在登录...')
          // 存储令牌
          localStorage.setItem('token', response.data.access_token)

          setTimeout(() => {
            switchToLogin()
          }, 1500)
        }
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '注册服务异常')
      } finally {
        isRegisterLoading.value = false
      }
    } else {
      ElMessage.error('请检查表单填写是否完整')
    }
  })
}
</script>

<style scoped>
/* ================= 全局与布局 ================= */
.login-page { display: flex; width: 100vw; height: 100vh; background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%); overflow: hidden; }

.left-section { flex: 1; background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%); display: flex; align-items: center; justify-content: center; color: white; position: relative; overflow: hidden; }
.left-section::before { content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 60%); animation: pulse 15s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.1); } }
.brand-content { text-align: center; max-width: 400px; padding: 20px; z-index: 1; }
.logo-icon { width: 80px; height: 80px; background: white; border-radius: 16px; margin: 0 auto 24px; position: relative; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2); }
.logo-icon::before { content: '🔍'; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 40px; }
.project-title { font-size: 36px; font-weight: 700; margin: 10px 0 8px; }
.project-desc { font-size: 16px; opacity: 0.9; line-height: 1.6; }

/* ================= 右侧与堆叠容器 ================= */
.right-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

/* 适配超长表单，容器变高变宽 */
.card-wrapper {
  width: 100%;
  max-width: 580px; /* 加宽以容纳双列网格 */
  height: 680px;    /* 固定高度，内部滚动 */
  position: relative;
}

/* 卡片基础设置 */
.card {
  width: 100%;
  height: 100%;
  position: absolute;
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  box-sizing: border-box;
  border-radius: 16px !important;
  cursor: default;
  border: none;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08) !important;
}

/* 滚动条美化 */
:deep(.el-card__body)::-webkit-scrollbar { width: 6px; }
:deep(.el-card__body)::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 3px; }
:deep(.el-card__body)::-webkit-scrollbar-track { background: transparent; }

/* 交互失活阻断 */
.card.is-inactive { cursor: pointer; }
.card.is-inactive :deep(.el-card__body) { pointer-events: none; overflow: hidden; }

/* --- 登录层（上层）动画 --- */
.login-card { z-index: 3; top: 0; left: 0; }
.login-card.slideOut {
  transform: translate(-32px, -32px) scale(0.96);
  opacity: 0.5;
  z-index: 2;
  background: #f8fafc;
}

/* --- 注册层（下层）动画 --- */
.lower-card { z-index: 2; top: 32px; left: 32px; opacity: 0.85; background: #f8fafc; }
.lower-card.slideIn {
  transform: translate(-32px, -32px);
  opacity: 1;
  z-index: 3;
  background: #ffffff;
}

/* --- 悬停微动效 --- */
.login-card.is-inactive:hover { transform: translate(-40px, -40px) scale(0.96); opacity: 0.7; }
.lower-card.is-inactive:hover {
  transform: translate(36px, 20px);
  opacity: 1;
  box-shadow: 0 16px 32px rgba(0, 0, 0, 0.15) !important;
}

/* ================= 卡片内部排版 ================= */
.auth-header h2, .form-title { font-size: 26px; font-weight: 600; margin: 0 0 8px; color: #111827; }
.auth-header p, .form-subtitle { color: #6b7280; margin-bottom: 24px; font-size: 14px; }

/* 注册头部与返回按钮 */
.register-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.back-btn { font-weight: 500; }

/* 居中底层的teaser内容 */
.teaser-content { height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }

/* 双列网格 */
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 20px; }
.form-label { display: block; font-size: 13px; font-weight: 500; color: #374151; margin-bottom: 6px; }

:deep(.el-form-item) { margin-bottom: 18px; }
:deep(.el-input__wrapper), :deep(.el-select__wrapper) { border-radius: 8px; padding: 6px 14px; }
.w-100 { width: 100%; }

/* 头像上传 */
.avatar-item { display: flex; flex-direction: column; align-items: center; grid-column: 1 / -1; margin-bottom: 20px; }
.avatar-uploader { border: 1px dashed #dcdfe6; border-radius: 50%; cursor: pointer; width: 80px; height: 80px; display: flex; justify-content: center; align-items: center; background: #fafafa; transition: 0.3s; }
.avatar-uploader:hover { border-color: #2563eb; }
.avatar-uploader-icon { font-size: 24px; color: #8c939d; }
.avatar { width: 80px; height: 80px; border-radius: 50%; object-fit: cover; }

/* 按钮与提示 */
.submit-btn { width: 100%; height: 44px; border-radius: 8px; font-size: 15px; }
.submit-item { grid-column: 1 / -1; }
.action-row { display: flex; justify-content: space-between; align-items: center; width: 100%; }
.error-tip { color: #dc2626; font-size: 13px; margin-bottom: 12px; padding: 8px 12px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; }

/* ================= 弹出悬浮层 ================= */
:deep(.custom-register-popover) { border-radius: 12px; padding: 12px; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15) !important; border: none; }
.popover-inner-content { display: flex; flex-direction: column; gap: 12px; }
.api-image-placeholder { width: 100%; height: 110px; background: #f3f4f6; border-radius: 8px; border: 1px dashed #d1d5db; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #9ca3af; transition: 0.3s; }
.api-image-placeholder .img-icon { font-size: 28px; margin-bottom: 6px; }
.popover-text { text-align: center; font-size: 14px; color: #4b5563; font-weight: 500; }
.highlight { color: #2563eb; font-weight: 600; }

/* ================= 响应式降级 ================= */
@media (max-width: 900px) {
  .login-page { flex-direction: column; overflow-y: auto; }
  .left-section { max-width: 100%; flex: none; padding: 40px 20px; }
  .right-section { padding: 20px; }

  .card-wrapper { height: auto; max-width: 100%; }

  /* 移动端取消绝对定位的物理堆叠，改为平铺并用 v-show 切换 */
  .card { position: relative; top: 0 !important; left: 0 !important; transform: none !important; margin-bottom: 20px; height: auto; }
  .card.is-inactive { display: none; } /* 移动端隐藏未激活的卡片 */
  .card.is-inactive :deep(.el-card__body) { pointer-events: auto; }

  .form-grid { grid-template-columns: 1fr; }
  :deep(.custom-register-popover) { display: none !important; }
}
</style>
