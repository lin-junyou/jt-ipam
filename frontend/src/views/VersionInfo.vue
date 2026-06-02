<script setup lang="ts">
/** 版本資訊（管理）：現行版本 + Python / 套件版本，並可檢查 GitHub 最新版。 */
import { onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import {
  NCard, NSpace, NIcon, NButton, NDescriptions, NDescriptionsItem, NTag,
  NDataTable, NAlert, NSpin, useMessage, type DataTableColumns,
} from "naive-ui";
import { SettingsIcon, RefreshIcon } from "@/icons";
import {
  getVersionInfo, checkLatestVersion, type VersionInfo, type LatestVersion,
} from "@/api/system";

const { t } = useI18n();
const msg = useMessage();

const info = ref<VersionInfo | null>(null);
const loading = ref(false);
const latest = ref<LatestVersion | null>(null);
const checking = ref(false);

const pkgRows = ref<{ name: string; version: string }[]>([]);

async function load() {
  loading.value = true;
  try {
    info.value = await getVersionInfo();
    pkgRows.value = Object.entries(info.value.packages)
      .map(([name, version]) => ({ name, version: version ?? "—" }));
  } catch {
    msg.error(t("errors.network"));
  } finally {
    loading.value = false;
  }
}

async function check() {
  checking.value = true;
  latest.value = null;
  try {
    latest.value = await checkLatestVersion();
    if (latest.value.error) msg.warning(t("version.check_failed"));
  } catch {
    msg.error(t("errors.network"));
  } finally {
    checking.value = false;
  }
}

const pkgCols: DataTableColumns<{ name: string; version: string }> = [
  { title: () => t("version.package"), key: "name", sorter: (a, b) => a.name.localeCompare(b.name) },
  { title: () => t("version.installed"), key: "version" },
];

onMounted(load);
</script>

<template>
  <n-card>
    <template #header>
      <n-space align="center" :wrap-item="false">
        <n-icon :size="22"><SettingsIcon /></n-icon>
        <span>{{ t("version.title") }}</span>
      </n-space>
    </template>

    <n-spin :show="loading">
      <n-descriptions v-if="info" bordered :column="1" label-placement="left"
                      label-style="width: 180px" style="margin-bottom: 16px">
        <n-descriptions-item :label="t('version.current')">
          <n-tag type="success" size="small">v{{ info.current }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="Python">{{ info.python }}</n-descriptions-item>
      </n-descriptions>

      <!-- 檢查最新版 -->
      <n-space align="center" style="margin-bottom: 16px">
        <n-button type="primary" :loading="checking" @click="check">
          <template #icon><n-icon><RefreshIcon /></n-icon></template>
          {{ t("version.check_latest") }}
        </n-button>
        <template v-if="latest && !latest.error">
          <n-tag v-if="latest.update_available" type="warning">
            {{ t("version.update_available", { v: latest.latest }) }}
          </n-tag>
          <n-tag v-else type="success">{{ t("version.up_to_date") }}</n-tag>
          <a :href="latest.release_url" target="_blank" rel="noopener">{{ t("version.releases") }}</a>
        </template>
        <n-tag v-else-if="latest && latest.error" type="error">{{ t("version.check_failed") }}</n-tag>
      </n-space>

      <n-alert type="info" :bordered="false" style="margin-bottom: 12px">
        {{ t("version.packages_hint") }}
      </n-alert>
      <n-data-table :columns="pkgCols" :data="pkgRows" size="small"
                    :bordered="false" :pagination="false" />
    </n-spin>
  </n-card>
</template>
