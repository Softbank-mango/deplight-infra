"""
AppSpec templates for CodeDeploy Blue-Green deployment
CodeDeploy 담당자가 이 파일을 수정하면 Lambda가 자동으로 반영합니다.
"""

APPSPEC_TEMPLATE = """version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: <TASK_DEFINITION>
        LoadBalancerInfo:
          ContainerName: "app"
          ContainerPort: {port}
        PlatformVersion: "LATEST"

Hooks:
  - BeforeInstall: "LambdaFunctionToValidateBeforeInstall"
  - AfterInstall: "LambdaFunctionToValidateAfterInstall"
  - AfterAllowTestTraffic: "LambdaFunctionToValidateAfterTestTrafficStarts"
  - BeforeAllowTraffic: "LambdaFunctionToValidateBeforeAllowingProductionTraffic"
  - AfterAllowTraffic: "LambdaFunctionToValidateAfterAllowingProductionTraffic"
"""


def generate_appspec(port: int) -> str:
    """AppSpec YAML 생성"""
    return APPSPEC_TEMPLATE.format(port=port)
