<template>
  <div>
    <!-- Rollback Button -->
    <v-btn
      :color="isProd ? 'error' : 'warning'"
      :variant="isProd ? 'outlined' : 'elevated'"
      :loading="loading"
      @click="dialogOpen = true"
      prepend-icon="mdi-undo"
    >
      롤백
      <v-chip v-if="isProd" color="error" size="small" class="ml-2">PROD</v-chip>
    </v-btn>

    <!-- Confirmation Dialog -->
    <v-dialog
      v-model="dialogOpen"
      max-width="600"
      persistent
    >
      <v-card>
        <v-card-title class="text-h5">
          {{ isProd ? '🔴 Production 배포 롤백' : '🟡 Dev 배포 롤백' }}
        </v-card-title>

        <v-card-text>
          <v-alert
            :type="isProd ? 'error' : 'warning'"
            variant="tonal"
            class="mb-4"
          >
            {{ isProd
              ? '⚠️ Production 환경을 이전 버전으로 롤백합니다. 이 작업은 실제 서비스에 영향을 줍니다.'
              : '이 환경을 이전 버전으로 롤백합니다.'
            }}
          </v-alert>

          <p class="text-h6 mb-3">정말로 롤백하시겠습니까?</p>

          <v-sheet class="pa-4 bg-grey-lighten-4 rounded mb-4">
            <div class="text-body-2 mb-1">
              <strong>환경:</strong> {{ environment }}
            </div>
            <div v-if="currentImageTag" class="text-body-2 mb-1">
              <strong>현재 버전:</strong> {{ currentImageTag }}
            </div>
            <div class="text-body-2 mb-1">
              <strong>롤백 대상:</strong> 마지막 성공한 배포 버전
            </div>
            <div class="text-body-2">
              <strong>예상 소요 시간:</strong> 3-5분
            </div>
          </v-sheet>

          <p class="text-body-2 mb-2">롤백 프로세스:</p>
          <ol class="text-body-2 text-grey-darken-1">
            <li>마지막 성공한 배포 버전 확인</li>
            <li>GitHub Actions 롤백 워크플로우 시작</li>
            <li>ECS 서비스 업데이트</li>
            <li>서비스 안정화 대기</li>
            <li>롤백 완료 확인</li>
          </ol>
        </v-card-text>

        <v-card-actions class="px-6 pb-4">
          <v-spacer></v-spacer>
          <v-btn
            @click="dialogOpen = false"
            :disabled="loading"
          >
            취소
          </v-btn>
          <v-btn
            :color="isProd ? 'error' : 'warning'"
            variant="elevated"
            :loading="loading"
            @click="handleRollback"
            prepend-icon="mdi-undo"
          >
            {{ isProd ? '확인 (PROD 롤백)' : '확인 (롤백 실행)' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar for notifications -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="6000"
      location="top"
    >
      {{ snackbar.message }}
      <template v-slot:actions>
        <v-btn
          variant="text"
          @click="snackbar.show = false"
        >
          닫기
        </v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

interface Props {
  environment: 'dev' | 'prod';
  currentImageTag?: string;
  userId: string;
  apiEndpoint: string;
}

interface RollbackResponse {
  status: string;
  message: string;
  data: {
    audit_id: string;
    workflow_run_id: string;
    environment: string;
    rollback_type: string;
    image_tag: string;
    estimated_duration: string;
    monitor_url: string;
  };
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: 'success', data: RollbackResponse): void;
  (e: 'error', error: Error): void;
}>();

const dialogOpen = ref(false);
const loading = ref(false);
const snackbar = ref({
  show: false,
  message: '',
  color: 'info',
});

const isProd = computed(() => props.environment === 'prod');

const handleRollback = async () => {
  loading.value = true;

  try {
    const response = await fetch(props.apiEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        environment: props.environment,
        rollback_type: 'terraform',
        user_id: props.userId,
        reason: `Manual rollback via UI by ${props.userId}`,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: RollbackResponse = await response.json();

    if (data.status === 'success') {
      snackbar.value = {
        show: true,
        message: `✅ 롤백이 시작되었습니다! (예상 소요 시간: ${data.data.estimated_duration})`,
        color: 'success',
      };

      emit('success', data);

      // Open monitoring page
      setTimeout(() => {
        window.open(data.data.monitor_url, '_blank');
      }, 2000);
    } else {
      throw new Error(data.message || 'Rollback failed');
    }
  } catch (error) {
    console.error('Rollback error:', error);

    snackbar.value = {
      show: true,
      message: `❌ 롤백 실행 실패: ${(error as Error).message}`,
      color: 'error',
    };

    emit('error', error as Error);
  } finally {
    loading.value = false;
    dialogOpen.value = false;
  }
};
</script>

<style scoped>
/* Add custom styles if needed */
</style>
