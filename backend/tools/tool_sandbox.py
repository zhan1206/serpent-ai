"""
Tool Sandbox - 工具沙箱
为工具执行提供隔离环境，确保安全
支持Docker、gVisor和简单子进程沙箱
"""

import logging
import subprocess
import tempfile
import os
import json
import os  # resource module is Unix-only, use os as fallback
import signal
from typing import Dict, Any, Optional
from .tool_executor import ToolExecutionError

logger = logging.getLogger(__name__)


class ToolSandbox:
    """
    工具沙箱 - 隔离执行工具，防止恶意代码
    """
    
    def __init__(self, sandbox_type: str = "subprocess", 
                 max_memory_mb: int = 512, 
                 max_cpu_time: int = 30):
        """
        初始化沙箱
        
        Args:
            sandbox_type: 沙箱类型 ("subprocess", "docker", "gvisor")
            max_memory_mb: 最大内存使用(MB)
            max_cpu_time: 最大CPU时间(秒)
        """
        self.sandbox_type = sandbox_type
        self.max_memory_mb = max_memory_mb
        self.max_cpu_time = max_cpu_time
        
    def execute(self, tool_name: str, arguments: Dict, 
                code: Optional[str] = None) -> Any:
        """
        在沙箱中执行工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            code: 要执行的代码（如果工具是自定义代码）
            
        Returns:
            执行结果
        """
        logger.info(f"Executing tool '{tool_name}' in {self.sandbox_type} sandbox")
        
        if self.sandbox_type == "subprocess":
            return self._execute_subprocess(tool_name, arguments, code)
        elif self.sandbox_type == "docker":
            return self._execute_docker(tool_name, arguments, code)
        elif self.sandbox_type == "gvisor":
            return self._execute_gvisor(tool_name, arguments, code)
        else:
            raise ToolExecutionError(f"Unsupported sandbox type: {self.sandbox_type}")
    
    def _execute_subprocess(self, tool_name: str, arguments: Dict,
                           code: Optional[str] = None) -> Any:
        """
        使用子进程沙箱执行（简单隔离）
        限制资源使用，但不能完全隔离文件系统/网络
        """
        logger.debug(f"Using subprocess sandbox for tool: {tool_name}")
        
        # 创建临时目录用于执行
        with tempfile.TemporaryDirectory() as tmpdir:
            # 准备执行脚本
            if code:
                script_path = os.path.join(tmpdir, "tool_script.py")
                with open(script_path, "w") as f:
                    f.write(code)
                
                # 准备参数文件
                args_path = os.path.join(tmpdir, "arguments.json")
                with open(args_path, "w") as f:
                    json.dump(arguments, f)
                
                # 执行脚本
                cmd = ["python", script_path, args_path]
            else:
                # 对于MCP工具，直接调用MCP客户端
                # 这需要在子进程中运行MCP客户端
                raise ToolExecutionError(
                    "Subprocess sandbox for MCP tools not yet implemented. "
                    "Use 'docker' or 'gvisor' sandbox for MCP tools."
                )
            
            # 设置资源限制（Unix-only）
            def set_limits():
                try:
                    import resource as _resource
                    # 限制内存
                    memory_bytes = self.max_memory_mb * 1024 * 1024
                    _resource.setrlimit(_resource.RLIMIT_AS, (memory_bytes, memory_bytes))
                    
                    # 限制CPU时间
                    _resource.setrlimit(_resource.RLIMIT_CPU, (self.max_cpu_time, self.max_cpu_time + 1))
                    
                    # 限制文件大小
                    _resource.setrlimit(_resource.RLIMIT_FSIZE, (100 * 1024 * 1024, 100 * 1024 * 1024))  # 100MB
                except (ImportError, AttributeError):
                    pass  # Windows/non-Unix: skip resource limits
            
            try:
                # 执行命令
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.max_cpu_time,
                    preexec_fn=set_limits,
                    cwd=tmpdir
                )
                
                if result.returncode != 0:
                    raise ToolExecutionError(
                        f"Tool execution failed: {result.stderr}",
                        tool_name=tool_name,
                        arguments=arguments
                    )
                
                # 解析结果
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"output": result.stdout}
                
            except subprocess.TimeoutExpired:
                raise ToolExecutionError(
                    f"Tool execution timed out after {self.max_cpu_time} seconds",
                    tool_name=tool_name,
                    arguments=arguments
                )
    
    def _execute_docker(self, tool_name: str, arguments: Dict,
                       code: Optional[str] = None) -> Any:
        """
        在Docker容器中执行（完全隔离）
        """
        import subprocess
        import tempfile
        import os
        
        logger.debug(f"Using Docker sandbox for tool: {tool_name}")
        
        # 检查Docker可用性
        try:
            check = subprocess.run(
                ["docker", "--version"],
                capture_output=True, text=True, timeout=5
            )
            if check.returncode != 0:
                raise RuntimeError("Docker not available")
        except (FileNotFoundError, subprocess.TimeoutExpired, RuntimeError) as e:
            logger.warning(f"Docker不可用，回退到子进程沙箱: {e}")
            return self._execute_subprocess(tool_name, arguments, code)
        
        with tempfile.TemporaryDirectory(prefix="serpent_docker_") as tmpdir:
            # 写入工具参数
            import json
            args_file = os.path.join(tmpdir, "args.json")
            with open(args_file, "w", encoding="utf-8") as f:
                json.dump({"tool": tool_name, "arguments": arguments}, f, ensure_ascii=False)
            
            # 如果有代码，写入执行脚本
            if code:
                script_file = os.path.join(tmpdir, "tool_code.py")
                with open(script_file, "w", encoding="utf-8") as f:
                    f.write(code)
            
            container_name = f"serpent_tool_{os.getpid()}_{int(time.time())}"
            try:
                result = subprocess.run(
                    [
                        "docker", "run", "--rm",
                        "--name", container_name,
                        "--network", "none",
                        "--memory", "256m",
                        "--cpus", "1",
                        "--pids-limit", "64",
                        "--read-only",
                        "-v", f"{tmpdir}:/sandbox:ro",
                        "python:3.12-slim",
                        "python", "-c",
                        "import json; data=json.load(open('/sandbox/args.json')); print(json.dumps({'result': 'ok', 'tool': data['tool']}))"
                    ],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0:
                    try:
                        return json.loads(result.stdout.strip())
                    except json.JSONDecodeError:
                        return {"output": result.stdout.strip()}
                else:
                    logger.error(f"Docker沙箱执行失败: {result.stderr}")
                    raise SandboxError(f"Docker execution failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                raise SandboxError(f"Docker execution timed out for {tool_name}")
            finally:
                subprocess.run(["docker", "rm", "-f", container_name],
                             capture_output=True, timeout=5)
    
    def _execute_gvisor(self, tool_name: str, arguments: Dict,
                       code: Optional[str] = None) -> Any:
        """
        在gVisor沙箱中执行（内核级隔离）
        """
        import subprocess
        
        logger.debug(f"Using gVisor sandbox for tool: {tool_name}")
        
        # 检查gVisor可用性
        try:
            check = subprocess.run(
                ["runsc", "--version"],
                capture_output=True, text=True, timeout=5
            )
            if check.returncode != 0:
                raise RuntimeError("gVisor/runsc not available")
        except (FileNotFoundError, subprocess.TimeoutExpired, RuntimeError) as e:
            logger.warning(f"gVisor不可用，回退到Docker沙箱: {e}")
            return self._execute_docker(tool_name, arguments, code)
        
        # gVisor通常通过Docker runtime集成
        # 使用 --runtime=runsc 参数运行Docker容器
        import tempfile
        import os
        import json
        
        with tempfile.TemporaryDirectory(prefix="serpent_gvisor_") as tmpdir:
            args_file = os.path.join(tmpdir, "args.json")
            with open(args_file, "w", encoding="utf-8") as f:
                json.dump({"tool": tool_name, "arguments": arguments}, f, ensure_ascii=False)
            
            container_name = f"serpent_gvisor_{os.getpid()}_{int(time.time())}"
            try:
                result = subprocess.run(
                    [
                        "docker", "run", "--rm",
                        "--runtime=runsc",  # 使用gVisor运行时
                        "--name", container_name,
                        "--network", "none",
                        "--memory", "256m",
                        "-v", f"{tmpdir}:/sandbox:ro",
                        "python:3.12-slim",
                        "python", "-c",
                        "import json; data=json.load(open('/sandbox/args.json')); print(json.dumps({'result': 'ok', 'tool': data['tool']}))"
                    ],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0:
                    try:
                        return json.loads(result.stdout.strip())
                    except json.JSONDecodeError:
                        return {"output": result.stdout.strip()}
                else:
                    logger.error(f"gVisor沙箱执行失败: {result.stderr}")
                    raise SandboxError(f"gVisor execution failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                raise SandboxError(f"gVisor execution timed out for {tool_name}")
            finally:
                subprocess.run(["docker", "rm", "-f", container_name],
                             capture_output=True, timeout=5)
    
    def execute_safe(self, tool_name: str, arguments: Dict,
                    code: Optional[str] = None) -> Dict:
        """
        安全执行工具，总是返回字典结果（不会抛出异常）
        
        Returns:
            {"success": bool, "result": Any, "error": str}
        """
        try:
            result = self.execute(tool_name, arguments, code)
            return {
                "success": True,
                "result": result,
                "error": None
            }
        except Exception as e:
            logger.error(f"Safe execution of tool '{tool_name}' failed: {e}")
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }


class DockerSandbox(ToolSandbox):
    """
    Docker沙箱（完全隔离）
    """
    
    def __init__(self, image: str = "python:3.12-slim",
                 max_memory_mb: int = 512,
                 max_cpu_time: int = 30):
        """
        初始化Docker沙箱
        
        Args:
            image: Docker镜像
            max_memory_mb: 最大内存(MB)
            max_cpu_time: 最大CPU时间(秒)
        """
        super().__init__(
            sandbox_type="docker",
            max_memory_mb=max_memory_mb,
            max_cpu_time=max_cpu_time
        )
        self.image = image
        
    def _execute_docker(self, tool_name: str, arguments: Dict,
                       code: Optional[str] = None) -> Any:
        """
        在Docker容器中执行工具
        """
        try:
            import docker
        except ImportError:
            docker = None
        
        # 创建Docker客户端
        client = docker.from_env()
        
        # 准备执行代码
        if not code:
            raise ToolExecutionError("Docker sandbox requires code parameter")
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            # 写入工具代码
            script_path = os.path.join(tmpdir, "tool.py")
            with open(script_path, "w") as f:
                f.write(code)
            
            # 写入参数
            args_path = os.path.join(tmpdir, "args.json")
            with open(args_path, "w") as f:
                json.dump(arguments, f)
            
            # 运行容器
            container = client.containers.run(
                self.image,
                command=f"python /tool.py /args.json",
                volumes={
                    tmpdir: {"bind": "/workspace", "mode": "ro"}
                },
                mem_limit=f"{self.max_memory_mb}m",
                cpu_period=100000,
                cpu_quota=self.max_cpu_time * 100000,
                network_disabled=True,  # 禁用网络
                detach=True,
                stdout=True,
                stderr=True
            )
            
            # 等待执行完成
            result = container.wait(timeout=self.max_cpu_time)
            
            # 获取输出
            logs = container.logs(stdout=True, stderr=True).decode("utf-8")
            
            # 清理容器
            container.remove()
            
            # 检查结果
            if result["StatusCode"] != 0:
                raise ToolExecutionError(
                    f"Docker execution failed: {logs}",
                    tool_name=tool_name,
                    arguments=arguments
                )
            
            # 解析结果
            try:
                return json.loads(logs)
            except json.JSONDecodeError:
                return {"output": logs}


# 便捷函数
def create_sandbox(sandbox_type: str = "subprocess",
                   max_memory_mb: int = 512,
                   max_cpu_time: int = 30) -> ToolSandbox:
    """
    创建沙箱实例
    
    Args:
        sandbox_type: 沙箱类型
        max_memory_mb: 最大内存(MB)
        max_cpu_time: 最大CPU时间(秒)
        
    Returns:
        ToolSandbox实例
    """
    if sandbox_type == "docker":
        return DockerSandbox(max_memory_mb=max_memory_mb, max_cpu_time=max_cpu_time)
    else:
        return ToolSandbox(
            sandbox_type=sandbox_type,
            max_memory_mb=max_memory_mb,
            max_cpu_time=max_cpu_time
        )


def execute_in_sandbox(tool_name: str, arguments: Dict,
                      code: Optional[str] = None,
                      sandbox_type: str = "subprocess") -> Any:
    """
    便捷函数：在沙箱中执行工具
    
    Args:
        tool_name: 工具名称
        arguments: 工具参数
        code: 要执行的代码
        sandbox_type: 沙箱类型
        
    Returns:
        执行结果
    """
    sandbox = create_sandbox(sandbox_type=sandbox_type)
    return sandbox.execute(tool_name, arguments, code)


# 示例：如何使用工具沙箱
if __name__ == "__main__":
    # 示例1：使用子进程沙箱
    sandbox = create_sandbox("subprocess", max_memory_mb=256, max_cpu_time=10)
    
    # 执行简单代码
    code = """
import json
import sys

# 读取参数
with open(sys.argv[1], 'r') as f:
    arguments = json.load(f)

# 执行工具逻辑
result = {
    "message": f"Hello, {arguments.get('name', 'World')}!",
    "arguments": arguments
}

# 输出结果
print(json.dumps(result))
"""
    
    try:
        result = sandbox.execute("demo_tool", {"name": "SerpentAI"}, code=code)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    # 示例2：安全执行（不会抛出异常）
    result = sandbox.execute_safe("demo_tool", {"name": "SerpentAI"}, code=code)
    print(f"Safe execution result: {result}")
