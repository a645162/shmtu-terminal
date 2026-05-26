请你构建一个5人团队，1个dotnet,1个CMake,1个C++，1个rust server（react+rust）,1个tauri（react+rust）完成下面的几个任务：

# 独立服务状态监控（rust server）

请你将服务状态监控拿出来！成为一个独立的项目，放置在Server/目录中，单独创建一个sln,以及一个project,专门用于监控restful服务的状态，能不能实现呢？tcp服务的状态监控也可以，反正就是那边提供一个接口，用于展示服务的繁忙程度，c++版和dotnet版都要提供！然后这边能够统计！并且提供网页页面？搞一个react程序调用成熟的ant design,以及ant design的icon,我觉得这样比较合理！

# RUST ocr server

请你模仿dotnet的ocr server，构建一个rust版本的！

# C++版 Ocr Server 重构

项目相对路径：Server/shmtu-cas-ocr-server

## 项目git初始化

请你将项目挂载为一个git submodule！

## 项目架构重构

目前是cli+ocr合为一体！
希望你将他分开为：server/cli/lib,一共3部分！

也就是一共3个项目，server和cli都依赖于lib！

## RESTful API

请你参考shmtu-terminal-desktop/shmtu-dotnet-lib/ocr/shmtu-ocr-onnx-server的API设计！
保留TCP的设计，新增RESTful的设计！
不要加入服务状态监控！

此外，你觉得我现在的TCP设计怎么样？

## 并发

考虑使用协程等较新版本C++的特性！

请你充分考虑并发问题！

## NCNN

由于NCNN新版API有少量改进，但是我已经在安卓的JNI里面进行了修改，请你参考shmtu-terminal-android/shmtu_ocr/src/main/cpp！

## Docker

NCNN的优点就是支持Vulkan推理！
但是这个程序就不用支持ARM了x64就可以了！
你也可以参考dotnet版server的docker设计！

最后不要忘记编写一个docker-compose.yml,并且把核显(N卡)直通进去！
