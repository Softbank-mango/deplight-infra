/**
 * Rollback Button Component
 *
 * UI에서 배포 롤백을 트리거하는 컴포넌트
 * 확인 다이얼로그 포함
 */

import React, { useState } from 'react';
import {
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  CircularProgress,
  Alert,
  Snackbar,
  Typography,
  Box,
  Chip,
} from '@mui/material';
import { Undo as UndoIcon } from '@mui/icons-material';

interface RollbackButtonProps {
  environment: 'dev' | 'prod';
  currentImageTag?: string;
  userId: string;
  apiEndpoint: string; // Lambda API Gateway endpoint
  onSuccess?: (data: RollbackResponse) => void;
  onError?: (error: Error) => void;
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

export const RollbackButton: React.FC<RollbackButtonProps> = ({
  environment,
  currentImageTag,
  userId,
  apiEndpoint,
  onSuccess,
  onError,
}) => {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info';
  }>({
    open: false,
    message: '',
    severity: 'info',
  });

  const handleOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    if (!loading) {
      setOpen(false);
    }
  };

  const handleConfirm = async () => {
    setLoading(true);

    try {
      const response = await fetch(apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          environment,
          rollback_type: 'terraform', // or 'ecs-taskdef'
          user_id: userId,
          reason: `Manual rollback via UI by ${userId}`,
          // image_tag는 생략하면 자동으로 마지막 성공 버전 사용
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data: RollbackResponse = await response.json();

      if (data.status === 'success') {
        setSnackbar({
          open: true,
          message: `✅ 롤백이 시작되었습니다! (예상 소요 시간: ${data.data.estimated_duration})`,
          severity: 'success',
        });

        if (onSuccess) {
          onSuccess(data);
        }

        // 진행 상황 모니터링 페이지로 리다이렉트하거나
        // 모니터링 컴포넌트 표시
        setTimeout(() => {
          window.open(data.data.monitor_url, '_blank');
        }, 2000);
      } else {
        throw new Error(data.message || 'Rollback failed');
      }
    } catch (error) {
      console.error('Rollback error:', error);

      setSnackbar({
        open: true,
        message: `❌ 롤백 실행 실패: ${(error as Error).message}`,
        severity: 'error',
      });

      if (onError) {
        onError(error as Error);
      }
    } finally {
      setLoading(false);
      setOpen(false);
    }
  };

  const handleSnackbarClose = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  const isProd = environment === 'prod';

  return (
    <>
      <Button
        variant={isProd ? 'outlined' : 'contained'}
        color={isProd ? 'error' : 'warning'}
        startIcon={<UndoIcon />}
        onClick={handleOpen}
        disabled={loading}
      >
        롤백
        {isProd && <Chip label="PROD" color="error" size="small" sx={{ ml: 1 }} />}
      </Button>

      <Dialog
        open={open}
        onClose={handleClose}
        maxWidth="sm"
        fullWidth
        disableEscapeKeyDown={loading}
      >
        <DialogTitle>
          {isProd ? '🔴 Production 배포 롤백' : '🟡 Dev 배포 롤백'}
        </DialogTitle>

        <DialogContent>
          <Box sx={{ mb: 2 }}>
            <Alert severity={isProd ? 'error' : 'warning'}>
              {isProd
                ? '⚠️ Production 환경을 이전 버전으로 롤백합니다. 이 작업은 실제 서비스에 영향을 줍니다.'
                : '이 환경을 이전 버전으로 롤백합니다.'}
            </Alert>
          </Box>

          <DialogContentText component="div">
            <Typography variant="body1" gutterBottom>
              <strong>정말로 롤백하시겠습니까?</strong>
            </Typography>

            <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
              <Typography variant="body2" color="text.secondary">
                환경: <strong>{environment}</strong>
              </Typography>
              {currentImageTag && (
                <Typography variant="body2" color="text.secondary">
                  현재 버전: <strong>{currentImageTag}</strong>
                </Typography>
              )}
              <Typography variant="body2" color="text.secondary">
                롤백 대상: <strong>마지막 성공한 배포 버전</strong>
              </Typography>
              <Typography variant="body2" color="text.secondary">
                예상 소요 시간: <strong>3-5분</strong>
              </Typography>
            </Box>

            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              롤백 프로세스:
            </Typography>
            <ol style={{ fontSize: '0.875rem', color: 'rgba(0, 0, 0, 0.6)' }}>
              <li>마지막 성공한 배포 버전 확인</li>
              <li>GitHub Actions 롤백 워크플로우 시작</li>
              <li>ECS 서비스 업데이트</li>
              <li>서비스 안정화 대기</li>
              <li>롤백 완료 확인</li>
            </ol>
          </DialogContentText>
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleClose} disabled={loading}>
            취소
          </Button>
          <Button
            onClick={handleConfirm}
            variant="contained"
            color={isProd ? 'error' : 'warning'}
            disabled={loading}
            startIcon={loading ? <CircularProgress size={20} /> : <UndoIcon />}
          >
            {loading ? '롤백 진행 중...' : isProd ? '확인 (PROD 롤백)' : '확인 (롤백 실행)'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleSnackbarClose}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={handleSnackbarClose}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
          variant="filled"
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </>
  );
};

// 사용 예시:
export const ExampleUsage = () => {
  return (
    <div>
      <h1>Deployment Dashboard</h1>

      {/* Production 환경 */}
      <RollbackButton
        environment="prod"
        currentImageTag="abc123d"
        userId="user@example.com"
        apiEndpoint="https://your-api-gateway-url.amazonaws.com/rollback"
        onSuccess={(data) => {
          console.log('Rollback initiated:', data);
          // 추가 로직: 대시보드 업데이트, 알림 등
        }}
        onError={(error) => {
          console.error('Rollback failed:', error);
          // 추가 로직: 에러 로깅, 알림 등
        }}
      />

      {/* Dev 환경 */}
      <RollbackButton
        environment="dev"
        currentImageTag="xyz789a"
        userId="user@example.com"
        apiEndpoint="https://your-api-gateway-url.amazonaws.com/rollback"
      />
    </div>
  );
};

export default RollbackButton;
