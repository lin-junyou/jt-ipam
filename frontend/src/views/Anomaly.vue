<script setup lang="ts">
import { computed, ref } from "vue";
import { fmtDateTime } from "@/utils/datetime";
import { useI18n } from "vue-i18n";
import { h } from "vue";
import {
  NCard, NSpace, NIcon, NButton, NAlert, NStatistic, NGrid, NGi, NDataTable, NEmpty,
  useMessage, type DataTableColumns,
} from "naive-ui";
import { runAnomalyScan, type AnomalyReport } from "@/api/phase3";
import {
  AnomalyIcon, TestIcon, InfoIcon,
} from "@/icons";

const { t } = useI18n();
const msg = useMessage();
const loading = ref(false);
const report = ref<AnomalyReport | null>(null);
const lastRunAt = ref<string | null>(null);
const anyFindings = computed(() => {
  const r = report.value;
  return !!r && (r.ip_conflicts.length + r.mac_drifts.length + r.ghost_ips.length + r.unauthorized_ips.length) > 0;
});

const CATEGORIES = [
  { key: "ip_conflicts", label: () => t("anomaly.ip_conflicts") },
  { key: "mac_drifts", label: () => t("anomaly.mac_drifts") },
  { key: "ghost_ips", label: () => t("anomaly.ghost_ips") },
  { key: "unauthorized_ips", label: () => t("anomaly.unauthorized") },
] as const;

// 依資料 keys 動態產生欄位，把偵測結果以表格呈現（取代難讀的原始 JSON）
function colsFor(rows: Record<string, any>[]): DataTableColumns<any> {
  const keys: string[] = [];
  for (const r of rows) for (const k of Object.keys(r)) if (!keys.includes(k)) keys.push(k);
  return keys.map((k) => ({
    title: k, key: k, ellipsis: { tooltip: true },
    render: (r: any) => {
      const v = r[k];
      if (v == null) return "—";
      return typeof v === "object" ? h("code", { style: "font-size:11px" }, JSON.stringify(v)) : String(v);
    },
  }));
}

async function run() {
  loading.value = true;
  try {
    report.value = await runAnomalyScan();
    lastRunAt.value = fmtDateTime(new Date());
  } catch (e: any) {
    msg.error(e?.response?.data?.detail ?? t("errors.server"));
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <n-card>
    <template #header>
      <n-space align="center" :wrap-item="false">
        <n-icon :size="22"><AnomalyIcon /></n-icon>
        <span>{{ t("anomaly.title") }}</span>
      </n-space>
    </template>
    <n-space style="margin-bottom: 12px">
      <n-button type="primary" :loading="loading" @click="run">
        <template #icon><n-icon><TestIcon /></n-icon></template>
        {{ t("anomaly.run_scan") }}
      </n-button>
      <span v-if="lastRunAt" style="opacity: 0.7">
        {{ t("anomaly.last_run") }}: {{ lastRunAt }}
      </span>
    </n-space>

    <n-alert v-if="!report" type="info">
      <template #icon><n-icon><InfoIcon /></n-icon></template>
      {{ t("anomaly.help") }}
    </n-alert>

    <template v-if="report">
      <n-grid :cols="4" x-gap="12" style="margin-bottom: 16px">
        <n-gi>
          <n-statistic :label="t('anomaly.ip_conflicts')" :value="report.ip_conflicts.length" />
        </n-gi>
        <n-gi>
          <n-statistic :label="t('anomaly.mac_drifts')" :value="report.mac_drifts.length" />
        </n-gi>
        <n-gi>
          <n-statistic :label="t('anomaly.ghost_ips')" :value="report.ghost_ips.length" />
        </n-gi>
        <n-gi>
          <n-statistic :label="t('anomaly.unauthorized')" :value="report.unauthorized_ips.length" />
        </n-gi>
      </n-grid>
      <n-empty v-if="!anyFindings" :description="t('anomaly.none_found')" style="margin: 24px 0" />
      <template v-for="c in CATEGORIES" :key="c.key">
        <n-card v-if="(report?.[c.key]?.length ?? 0) > 0" size="small" style="margin-bottom: 12px"
                :title="`${c.label()} (${report?.[c.key]?.length ?? 0})`">
          <n-data-table :columns="colsFor(report?.[c.key] ?? [])" :data="report?.[c.key] ?? []"
                        :bordered="false" size="small" :scroll-x="600" />
        </n-card>
      </template>
    </template>
  </n-card>
</template>
