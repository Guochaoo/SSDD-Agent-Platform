<template>
  <div class="dashboard-page">
    <!-- header bar -->
    <div class="dash-header">
      <span class="dash-title">Dash board</span>
      <div class="dash-header-right">
        <div class="period-wrap" ref="periodRef">
        <button class="period-trigger" @click="menuOpen = !menuOpen">
          <span class="period-label">时间维度</span>
          <span class="period-val">{{ currentPeriodLabel }}</span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m6 9 6 6 6-6"/></svg>
        </button>
        <Teleport to="body">
          <div v-if="menuOpen" class="period-overlay" @click="closeMenu" />
          <transition name="period-drop">
            <div v-if="menuOpen" class="period-dropdown" :style="dropStyle" @click.stop>
              <div
                v-for="opt in periodOptions"
                :key="opt.value"
                :class="['period-item', { active: period === opt.value }]"
                @click="selectPeriod(opt.value)"
              >{{ opt.label }}</div>
            </div>
          </transition>
          <transition name="period-drop">
            <div v-if="menuOpen && period === 'custom'" class="period-cal-panel" :style="calPanelStyle" @click.stop>
              <div class="period-calendar">
                <div class="cal-month" v-for="(m, mi) in calendarMonths" :key="mi">
                  <div class="cal-month-head">
                    <button v-if="mi === 0" class="cal-nav" @click.stop="calMonthOffset--">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m15 18-6-6 6-6"/></svg>
                    </button>
                    <span v-else class="cal-nav-spacer" />
                    <span class="cal-month-title">{{ m.label }}</span>
                    <button v-if="mi === 1" class="cal-nav" @click.stop="calMonthOffset++">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m9 18 6-6-6-6"/></svg>
                    </button>
                    <span v-else class="cal-nav-spacer" />
                  </div>
                  <div class="cal-weekdays">
                    <span v-for="d in weekDays" :key="d" class="cal-wd">{{ d }}</span>
                  </div>
                  <div class="cal-grid">
                    <span
                      v-for="(day, di) in m.days"
                      :key="di"
                      :class="calDayClass(day)"
                      @click.stop="pickDate(day)"
                    >{{ day ? day.label : '' }}</span>
                  </div>
                </div>
              </div>
            </div>
          </transition>
        </Teleport>
      </div>
      <button class="period-trigger refresh-btn" :disabled="loading" @click="loadDashboard">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" :class="{ spin: loading }"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg>
        <span class="period-val">{{ text.refresh }}</span>
      </button>
      </div>
    </div>

    <PageErrorAlert
      v-if="pageError"
      :message="pageError"
      :retry-text="text.reload"
      @retry="loadDashboard"
    />

    <!-- metric header + sidebar cards on same row -->
    <div class="dash-top-row">
      <div class="chart-metric-header">
        <div class="chart-metric-label">检测次数</div>
        <div class="chart-metric-row">
          <span class="chart-metric-value">{{ trendTotal }}</span>
          <span class="chart-pill blue">{{ trendChangeText }}</span>
          <span class="chart-pill blue-light">{{ trendPrevTotal }} 次</span>
        </div>
        <div class="chart-compare-row">
          <span class="chart-compare-label">vs prev.</span>
          <span class="chart-compare-date" ref="trendCompareRef" @click.stop="toggleTrendCompareCal">
            {{ trendDateLabel }}
          </span>
          <Teleport to="body">
            <div v-if="trendCompareOpen" class="period-overlay" @click="trendCompareOpen = false" />
            <transition name="period-drop">
              <div v-if="trendCompareOpen" class="period-cal-panel" :style="trendCompareCalStyle" @click.stop>
                <div class="period-calendar">
                  <div class="cal-month" v-for="(m, mi) in trendCompareMonths" :key="mi">
                    <div class="cal-month-head">
                      <button v-if="mi === 0" class="cal-nav" @click.stop="tcMonthOffset--">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m15 18-6-6 6-6"/></svg>
                      </button>
                      <span v-else class="cal-nav-spacer" />
                      <span class="cal-month-title">{{ m.label }}</span>
                      <button v-if="mi === 1" class="cal-nav" @click.stop="tcMonthOffset++">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m9 18 6-6-6-6"/></svg>
                      </button>
                      <span v-else class="cal-nav-spacer" />
                    </div>
                    <div class="cal-weekdays">
                      <span v-for="d in weekDays" :key="d" class="cal-wd">{{ d }}</span>
                    </div>
                    <div class="cal-grid">
                      <span
                        v-for="(day, di) in m.days"
                        :key="di"
                        :class="tcDayClass(day)"
                        @click.stop="pickTrendCompareDate(day)"
                      >{{ day ? day.label : '' }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </transition>
          </Teleport>
        </div>
      </div>

      <div class="card card-light">
        <div class="card-icon-wrap">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M15 8C15 9.65685 13.6569 11 12 11C10.3431 11 9 9.65685 9 8C9 6.34315 10.3431 5 12 5C13.6569 5 15 6.34315 15 8Z" />
            <path d="M13.7143 14H10.2857C7.91876 14 6 15.9188 6 18.2857C6 19.2325 6.76749 20 7.71426 20H16.2857C17.2325 20 18 19.2325 18 18.2857C18 15.9188 16.0812 14 13.7143 14Z" />
          </svg>
        </div>
        <h4>检测概览</h4>
        <p class="card-text">
          累计检测图片 <b>{{ dashboard.totals.totalImages }}</b> 张，
          发现缺陷 <b>{{ dashboard.totals.totalObjects }}</b> 处。
        </p>
      </div>

      <div class="card card-dark">
        <p class="card-eyebrow">主要指标</p>
        <h4>检测任务完成率</h4>
        <div class="progress-wrap">
          <div class="progress-row">
            <span class="progress-val">{{ completionRate }}%</span>
            <span class="progress-target">目标 100%</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: completionRate + '%' }" />
          </div>
        </div>
      </div>
    </div>

    <!-- chart: full width below -->
    <EChartPanel :option="trendOption" :loading="loading" :empty="dashboard.dailyTrend.length === 0" height="300px" />

    <!-- KPI row -->
    <div class="kpi-row">
      <div class="kpi-card">
        <p class="kpi-label">训练任务</p>
        <div class="kpi-row-bottom">
          <p class="kpi-value">{{ dashboard.totals.trainingTasks || 0 }}<small>次</small></p>
        </div>
      </div>
      <div class="kpi-card">
        <p class="kpi-label">检测图片</p>
        <div class="kpi-row-bottom">
          <p class="kpi-value">{{ dashboard.totals.totalImages }}<small>张</small></p>
        </div>
      </div>
      <div class="kpi-card">
        <p class="kpi-label">缺陷目标</p>
        <div class="kpi-row-bottom">
          <p class="kpi-value">{{ dashboard.totals.totalObjects }}<small>处</small></p>
        </div>
      </div>
      <div class="kpi-card">
        <p class="kpi-label">平均耗时</p>
        <div class="kpi-row-bottom">
          <p class="kpi-value">{{ Number(dashboard.totals.avgInferenceTimeMs || 0).toFixed(1) }}<small>ms</small></p>
        </div>
      </div>
    </div>

    <!-- secondary charts -->
    <div class="dash-grid-secondary">
      <div class="card">
        <div class="card-head">
          <h3>{{ text.classTitle }}</h3>
          <span class="card-sub">{{ text.classSubtitle }}</span>
        </div>
        <EChartPanel :option="classOption" :loading="loading" :empty="dashboard.classDistribution.length === 0" height="300px" />
      </div>
      <div class="card">
        <div class="card-head">
          <h3>每日训练趋势</h3>
          <span class="card-sub">按创建日期统计训练任务</span>
        </div>
        <EChartPanel :option="trainingTrendOption" :loading="loading" :empty="dashboard.trainingDailyTrend.length === 0" height="300px" />
      </div>
    </div>

    <div class="dash-grid-secondary">
      <div class="card">
        <div class="card-head">
          <h3>{{ text.sceneTitle }}</h3>
          <span class="card-sub">{{ text.sceneSubtitle }}</span>
        </div>
        <EChartPanel :option="sceneOption" :loading="loading" :empty="dashboard.sceneDistribution.length === 0" height="300px" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useSettingsStore } from '@/stores/settings'
import { getDashboardApi } from "@/api/statistics";
import EChartPanel from "@/components/charts/EChartPanel.vue";
import PageErrorAlert from "@/components/common/PageErrorAlert.vue";
import { getApiErrorMessage } from "@/utils/apiError";

function last30Days() {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 29)
  return [fmtDate(start), fmtDate(end)]
}
function fmtDate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const loading = ref(false);
const settingsStore = useSettingsStore()
const pageError = ref("");
const period = ref('30d');
const menuOpen = ref(false);
const periodRef = ref(null);
const filters = reactive({ dateRange: last30Days() });

const periodOptions = [
  { label: '近 7 天', value: '7d' },
  { label: '近 30 天', value: '30d' },
  { label: '本月', value: 'month' },
  { label: '自定义', value: 'custom' },
]

const currentPeriodLabel = computed(() => {
  const found = periodOptions.find(o => o.value === period.value)
  return found ? found.label : '近 30 天'
})

const dropStyle = computed(() => {
  if (!periodRef.value) return {}
  const r = periodRef.value.getBoundingClientRect()
  return { position: 'fixed', top: r.bottom + 6 + 'px', left: r.left + 'px', minWidth: r.width + 'px' }
})

// Calendar panel to the left of the dropdown
const calPanelStyle = computed(() => {
  if (!periodRef.value) return {}
  const r = periodRef.value.getBoundingClientRect()
  return { position: 'fixed', top: r.bottom + 6 + 'px', right: window.innerWidth - r.left + 10 + 'px' }
})

function closeMenu() {
  if (period.value !== 'custom') {
    menuOpen.value = false
  }
}

function selectPeriod(val) {
  if (val === 'custom') {
    period.value = 'custom'
    // restore previous selection
    calSelStart.value = filters.dateRange[0] || null
    calSelEnd.value = filters.dateRange[1] || null
    return
  }
  period.value = val
  menuOpen.value = false
  prevDateOverride.value = null
  if (val === '7d') {
    const end = new Date(); const start = new Date()
    start.setDate(start.getDate() - 6)
    filters.dateRange = [fmtDate(start), fmtDate(end)]
  } else if (val === '30d') {
    filters.dateRange = last30Days()
  } else if (val === 'month') {
    const now = new Date()
    const start = new Date(now.getFullYear(), now.getMonth(), 1)
    filters.dateRange = [fmtDate(start), fmtDate(now)]
  }
  loadDashboard()
}

function onCustomDateChange() {
  menuOpen.value = false
  loadDashboard()
}

// ── custom calendar ──
const calMonthOffset = ref(-1)
const calSelStart = ref(null)
const calSelEnd = ref(null)

const weekDays = ['日', '一', '二', '三', '四', '五', '六']

const calendarMonths = computed(() => {
  const ms = []
  for (let i = 0; i < 2; i++) {
    const now = new Date()
    const ym = new Date(now.getFullYear(), now.getMonth() + calMonthOffset.value + i, 1)
    const year = ym.getFullYear()
    const month = ym.getMonth()
    const firstDow = new Date(year, month, 1).getDay()
    const daysInMonth = new Date(year, month + 1, 0).getDate()
    const days = []
    for (let d = 0; d < firstDow; d++) days.push(null)
    for (let d = 1; d <= daysInMonth; d++) {
      days.push({ label: d, date: fmtDate(new Date(year, month, d)) })
    }
    ms.push({ label: `${year}年${month + 1}月`, days })
  }
  return ms
})

function calDayClass(day) {
  if (!day) return 'cal-day-empty'
  const d = day.date
  const s = calSelStart.value
  const e = calSelEnd.value
  const today = fmtDate(new Date())
  const cls = ['cal-day']
  if (d > today) cls.push('future')
  if (d === s || d === e) cls.push('active')
  else if (s && e && d > s && d < e) cls.push('in-range')
  return cls.join(' ')
}

function pickDate(day) {
  if (!day || day.date > fmtDate(new Date())) return
  if (!calSelStart.value || (calSelStart.value && calSelEnd.value)) {
    calSelStart.value = day.date
    calSelEnd.value = null
    return
  }
  if (day.date < calSelStart.value) {
    calSelStart.value = day.date
    calSelEnd.value = null
    return
  }
  calSelEnd.value = day.date
  filters.dateRange = [calSelStart.value, calSelEnd.value]
  prevDateOverride.value = null
  menuOpen.value = false
  period.value = 'custom'
  loadDashboard()
  // Keep selection visible briefly, then reset
  setTimeout(() => { calSelStart.value = null; calSelEnd.value = null }, 200)
}

function onClickOutside(e) {
  if (periodRef.value && !periodRef.value.contains(e.target)) {
    menuOpen.value = false
  }
}
onMounted(() => {
  document.addEventListener('click', onClickOutside)
  loadDashboard()
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutside)
})
const dashboard = reactive({
  totals: { totalTasks: 0, totalImages: 0, totalObjects: 0, avgInferenceTimeMs: 0, trainingTasks: 0 },
  classDistribution: [],
  dailyTrend: [],
  trainingDailyTrend: [],
  sceneDistribution: [],
  updatedAt: "",
});
const axisStyle = { axisLine: { lineStyle: { color: "#d0d5dd" } }, axisLabel: { color: "#667085" } };

const trendTotal = computed(() => {
  return dashboard.dailyTrend.reduce((s, d) => s + (d.tasks || 0), 0)
})

const trendPrevTotal = computed(() => {
  return dashboard.dailyTrend.reduce((s, d) => s + (d.tasks || 0), 0) || 0
})

const trendChange = computed(() => {
  if (!trendPrevTotal.value) return 0
  return Math.round(((trendTotal.value - trendPrevTotal.value) / trendPrevTotal.value) * 100)
})

const trendChangeText = computed(() => {
  const pct = trendChange.value
  if (pct > 0) return `↑${pct}%`
  if (pct < 0) return `↓${Math.abs(pct)}%`
  return '0%'
})

const prevDateOverride = ref(null) // null = auto-compute

const trendPrevRange = computed(() => {
  if (prevDateOverride.value) return { start: prevDateOverride.value.start, end: prevDateOverride.value.end }
  const [s, e] = filters.dateRange
  if (!s || !e) return { start: '', end: '' }
  const start = new Date(s)
  const end = new Date(e)
  const days = Math.round((end - start) / (1000 * 60 * 60 * 24))
  const prevEnd = new Date(start)
  prevEnd.setDate(prevEnd.getDate() - 1)
  const prevStart = new Date(prevEnd)
  prevStart.setDate(prevStart.getDate() - days)
  return { start: fmtDate(prevStart), end: fmtDate(prevEnd) }
})

const trendDateLabel = computed(() => {
  const { start, end } = trendPrevRange.value
  if (start && end) return `${start} — ${end}`
  return '选择日期范围'
})

const trendCompareOpen = ref(false)
const trendCompareRef = ref(null)
const tcMonthOffset = ref(-1)
const tcSelStart = ref(null)
const tcSelEnd = ref(null)

const trendCompareCalStyle = computed(() => {
  if (!trendCompareRef.value) return {}
  const r = trendCompareRef.value.getBoundingClientRect()
  return { position: 'fixed', top: r.bottom + 6 + 'px', left: r.left + 'px' }
})

const trendCompareMonths = computed(() => {
  const ms = []
  for (let i = 0; i < 2; i++) {
    const now = new Date()
    const ym = new Date(now.getFullYear(), now.getMonth() + tcMonthOffset.value + i, 1)
    const year = ym.getFullYear()
    const month = ym.getMonth()
    const firstDow = new Date(year, month, 1).getDay()
    const daysInMonth = new Date(year, month + 1, 0).getDate()
    const days = []
    for (let d = 0; d < firstDow; d++) days.push(null)
    for (let d = 1; d <= daysInMonth; d++) {
      days.push({ label: d, date: fmtDate(new Date(year, month, d)) })
    }
    ms.push({ label: `${year}年${month + 1}月`, days })
  }
  return ms
})

function tcDayClass(day) {
  if (!day) return 'cal-day-empty'
  const d = day.date
  const s = tcSelStart.value
  const e = tcSelEnd.value
  const today = fmtDate(new Date())
  const cls = ['cal-day']
  if (d > today) cls.push('future')
  if (d === s || d === e) cls.push('active')
  else if (s && e && d > s && d < e) cls.push('in-range')
  return cls.join(' ')
}

function pickTrendCompareDate(day) {
  if (!day || day.date > fmtDate(new Date())) return
  if (!tcSelStart.value || (tcSelStart.value && tcSelEnd.value)) {
    tcSelStart.value = day.date
    tcSelEnd.value = null
    return
  }
  if (day.date < tcSelStart.value) {
    tcSelStart.value = day.date
    tcSelEnd.value = null
    return
  }
  tcSelEnd.value = day.date
  prevDateOverride.value = { start: tcSelStart.value, end: tcSelEnd.value }
  trendCompareOpen.value = false
  tcSelStart.value = null
  tcSelEnd.value = null
}

function toggleTrendCompareCal() {
  trendCompareOpen.value = !trendCompareOpen.value
  if (trendCompareOpen.value) {
    const { start, end } = trendPrevRange.value
    tcSelStart.value = start || null
    tcSelEnd.value = end || null
    // Show the end date's month on the right panel
    if (end) {
      const endDate = new Date(end)
      const now = new Date()
      tcMonthOffset.value = (endDate.getFullYear() - now.getFullYear()) * 12 + (endDate.getMonth() - now.getMonth()) - 1
    } else {
      tcMonthOffset.value = -1
    }
  }
}

function openTrendDatePicker() {
  period.value = 'custom'
  menuOpen.value = true
  calMonthOffset.value = -1
  calSelStart.value = filters.dateRange[0] || null
  calSelEnd.value = filters.dateRange[1] || null
}

const completionRate = computed(() => {
  const total = dashboard.totals.totalTasks
  if (!total) return 0
  return Math.round((total / Math.max(total, 1)) * 100)
})

const text = computed(() => settingsStore.isEnglish ? {
  refresh: 'Refresh',
  reload: 'Reload',
  startDate: 'Start date',
  endDate: 'End date',
  trendTitle: 'Daily Detection Trend',
  trendSubtitle: 'Task count by creation date',
  classTitle: 'Defect Class Distribution',
  classSubtitle: 'Target counts in historical results',
  sceneTitle: 'Detection Scene Distribution',
  sceneSubtitle: 'Completed tasks by scene',
  taskSeries: 'Detection tasks',
  objectUnit: 'defects',
  loadFailed: 'Failed to load dashboard data',
} : {
  refresh: '刷新',
  reload: '重新加载',
  startDate: '开始日期',
  endDate: '结束日期',
  trendTitle: '每日检测任务趋势',
  trendSubtitle: '按创建日期统计检测任务数量',
  classTitle: '缺陷类别分布',
  classSubtitle: '当前账号历史结果中的目标数量',
  sceneTitle: '检测场景分布',
  sceneSubtitle: '已完成任务在各检测场景中的数量',
  taskSeries: '检测任务',
  objectUnit: '处',
  loadFailed: '看板数据加载失败',
})

const trendOption = computed(() => ({
  tooltip: { trigger: "axis" },
  color: ["#2563eb"],
  grid: { left: 48, right: 16, top: 16, bottom: 28 },
  xAxis: { type: "category", data: dashboard.dailyTrend.map((item) => item.date), ...axisStyle },
  yAxis: { type: "value", minInterval: 1, splitLine: { lineStyle: { color: "#edf0f5" } }, ...axisStyle },
  series: [{ name: text.value.taskSeries, type: "line", smooth: true, symbolSize: 6, areaStyle: { color: "rgba(37,99,235,.06)" }, data: dashboard.dailyTrend.map((item) => item.tasks) }],
}));

const classOption = computed(() => ({
  tooltip: { trigger: "item", formatter: `{b}<br/>{c} ${text.value.objectUnit} · {d}%` },
  color: ["#2563eb", "#7c3aed", "#06b6d4", "#10b981", "#f59e0b", "#f97316"],
  legend: { type: "scroll", orient: "vertical", right: 4, top: "middle" },
  series: [{ type: "pie", radius: ["43%", "70%"], center: ["38%", "53%"], avoidLabelOverlap: true, itemStyle: { borderColor: "#fff", borderWidth: 3 }, label: { show: false }, emphasis: { label: { show: true, fontSize: 15, fontWeight: "bold" } }, data: dashboard.classDistribution }],
}));

const trainingTrendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  color: ['#0ea5e9'],
  grid: { left: 48, right: 16, top: 16, bottom: 28 },
  xAxis: { type: 'category', data: dashboard.trainingDailyTrend.map((item) => item.date), ...axisStyle },
  yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: '#edf0f5' } }, ...axisStyle },
  series: [{ name: '训练任务', type: 'bar', data: dashboard.trainingDailyTrend.map((item) => item.tasks) }],
}));

const sceneOption = computed(() => ({
  tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
  color: ["#7c3aed"],
  grid: { left: 110, right: 20, top: 12, bottom: 24 },
  xAxis: { type: "value", minInterval: 1, splitLine: { lineStyle: { color: "#edf0f5" } }, ...axisStyle },
  yAxis: { type: "category", data: dashboard.sceneDistribution.map((item) => item.name), ...axisStyle },
  series: [{ type: "bar", barMaxWidth: 32, data: dashboard.sceneDistribution.map((item) => item.value), itemStyle: { borderRadius: [0, 6, 6, 0] } }],
}));

async function loadDashboard() {
  loading.value = true;
  pageError.value = "";
  try {
    const data = await getDashboardApi({
      startDate: filters.dateRange?.[0],
      endDate: filters.dateRange?.[1],
    });
    Object.assign(dashboard, data);
  } catch (error) {
    pageError.value = getApiErrorMessage(error, text.value.loadFailed);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadDashboard()
});
</script>

<style lang="scss" scoped>
.dashboard-page {
  padding: 0px 0px 0px;
  max-width: 1200px;
  margin: 0 auto;
}

.dash-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.dash-title {
  font-size: 40px;
  font-weight: 600;
  color: #8b8b94;
  letter-spacing: -0.3px;
}

.dash-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.period-wrap {
  position: relative;
}

.period-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border: 1px solid #d4d4d8;
  border-radius: 8px;
  background: #fff;
  color: #18181b;
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.15s;

  &:hover { border-color: #a1a1aa; }
}

.period-label {
  color: #71717a;
  font-weight: 400;

  &::after { content: ''; }
}

.period-val {
  font-weight: 500;
}

.refresh-btn {
  .spin {
    animation: dash-spin 1s linear infinite;
  }
}

@keyframes dash-spin {
  to { transform: rotate(360deg); }
}

/* dropdown */
.period-overlay {
  position: fixed;
  inset: 0;
  z-index: 2999;
}

.period-dropdown {
  z-index: 3000;
  min-width: 170px;
  background: #fff;
  border: 1px solid #e4e4e7;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.08), 0 8px 32px rgba(0,0,0,0.06);
  padding: 8px;
  display: flex;
  flex-direction: column;
}

.period-item {
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 14px;
  color: #18181b;
  cursor: pointer;
  transition: background 0.15s;

  &:hover { background: #f5f5f5; }

  &.active {
    background: #f5f5f5;
    font-weight: 600;
  }
}

.period-divider {
  height: 1px;
  background: #e4e4e7;
  margin: 6px 0;
}

.period-cal-panel {
  z-index: 3000;
  background: #fff;
  border: 1px solid #e4e4e7;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.08), 0 8px 32px rgba(0,0,0,0.06);
}

.period-calendar {
  display: flex;
  gap: 32px;
  padding: 8px 16px 4px;
}

.cal-month {
  flex: 1;
  min-width: 196px;
}

.cal-month-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  height: 28px;
}

.cal-nav {
  width: 28px; height: 28px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #52525b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover { background: #f4f4f5; }
}

.cal-nav-spacer {
  width: 28px; height: 28px;
}

.cal-month-title {
  font-size: 14px;
  font-weight: 600;
  color: #18181b;
}

.cal-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  margin-bottom: 4px;
}

.cal-wd {
  font-size: 12px;
  color: #a1a1aa;
  padding: 6px 0;
  font-weight: 500;
}

.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
}

.cal-day {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  width: 32px;
  justify-self: center;
  border-radius: 50%;
  font-size: 13px;
  color: #18181b;
  cursor: pointer;
  transition: background 0.12s;

  &:hover { background: #f4f4f5; }

  &.future {
    color: #d4d4d8;
    cursor: default;
    pointer-events: none;
  }

  &.active {
    background: #18181b;
    color: #fff;
    font-weight: 600;
  }

  &.in-range {
    background: #f5f5f5;
    border-radius: 0;
  }
}

.cal-day-empty {
  height: 32px;
}

.period-drop-enter-active { transition: all 0.15s ease-out; }
.period-drop-leave-active { transition: all 0.1s ease-in; }
.period-drop-enter-from { opacity: 0; transform: translateY(-4px); }
.period-drop-leave-to { opacity: 0; transform: translateY(-2px); }

/* cards */
.card {
  background: #fff;
  border: 1px solid #e4e4e7;
  border-radius: 14px;
  padding: 12px 16px;
}

.card-head {
  margin-bottom: 8px;

  h3 {
    margin: 0 0 2px;
    font-size: 16px;
    font-weight: 700;
    color: #18181b;
  }
}

.card-sub {
  font-size: 12px;
  color: #a1a1aa;
}

/* top row: metric header + sidebar */
.dash-top-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
  align-items: start;
}

.chart-metric-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.chart-metric-label {
  font-size: 16px;
  font-weight: 700;
  color: #18181b;
  margin-bottom: 4px;
}

.chart-metric-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.chart-metric-value {
  font-size: 32px;
  font-weight: 700;
  color: #18181b;
  letter-spacing: -0.5px;
  line-height: 1;
}

.chart-pill {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;

  &.blue {
    background: #eff6ff;
    color: #2563eb;
  }

  &.blue-light {
    background: #f4f4f5;
    color: #52525b;
  }
}

.chart-compare-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.chart-compare-label {
  font-size: 12px;
  color: #a1a1aa;
}

.chart-compare-date {
  font-size: 12px;
  color: #52525b;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;

  &:hover { color: #18181b; }
}

/* sidebar */
.side-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-dark {
  background: #18181b;
  color: #fff;
  border-color: #18181b;
  padding: 12px 16px;

  .card-eyebrow {
    margin: 0 0 2px;
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #71717a;
  }

  h4 {
    margin: 0 0 4px;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: -0.3px;
  }
}

.progress-wrap {
}

.progress-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 4px;
}

.progress-val {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: -1px;
}

.progress-target {
  font-size: 10px;
  color: #a1a1aa;
}

.progress-bar {
  width: 100%;
  height: 4px;
  background: #3f3f46;
  border-radius: 10px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #fff;
  border-radius: 10px;
  transition: width 0.6s ease;
}

.card-light {
  .card-icon-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 7px;
    background: #f4f4f5;
    border: 1px solid #e4e4e7;
    color: #18181b;
    margin-bottom: 6px;
  }

  h4 {
    margin: 0 0 4px;
    font-size: 14px;
    font-weight: 700;
    color: #18181b;
  }
}

.card-text {
  margin: 0;
  font-size: 12px;
  color: #71717a;
  line-height: 1.4;

  b {
    color: #18181b;
    font-weight: 600;
  }
}

/* KPI row */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.kpi-card {
  padding: 18px 20px;
  border-radius: 16px;
  border: 1px solid #e4e4e7;
  background: #fafafa;
  transition: all 0.25s;

  &:hover {
    border-color: #10b981;
    background: #f0fdf4;
  }
}

.kpi-label {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #a1a1aa;
}

.kpi-row-bottom {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.kpi-value {
  margin: 0;
  font-size: 26px;
  font-weight: 800;
  color: #18181b;
  letter-spacing: -0.5px;

  small {
    font-size: 12px;
    font-weight: 500;
    color: #a1a1aa;
    margin-left: 3px;
  }
}

/* secondary charts */
.dash-grid-secondary {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

@media (max-width: 980px) {
  .dash-top-row {
    grid-template-columns: 1fr;
  }
  .dash-grid-secondary {
    grid-template-columns: 1fr;
  }
}
</style>
