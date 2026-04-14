#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <cstdlib>
#include <filesystem>
#include <chrono>
#include "json.hpp"

using json = nlohmann::json;
namespace fs = std::filesystem;

// ─────────────────────────────────────────────
//  Structured log emitter → stdout (FastAPI reads these via SSE)
// ─────────────────────────────────────────────
void emit(const std::string& stage, const std::string& message, const std::string& level = "info") {
    json log;
    log["stage"]   = stage;
    log["message"] = message;
    log["level"]   = level;
    // ISO-like timestamp
    auto now_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()
    ).count();
    log["ts"] = now_ms;
    std::cout << log.dump() << std::endl;
    std::cout.flush();
}

// ─────────────────────────────────────────────
//  File scaffolder
// ─────────────────────────────────────────────
bool scaffold_files(const json& files, const std::string& workspace) {
    emit("scaffold", "Creating project workspace...");
    fs::create_directories(workspace);

    for (const auto& item : files.items()) {
        std::string rel_path    = item.key();
        std::string content     = item.value().get<std::string>();
        std::string full_path   = workspace + "/" + rel_path;

        fs::create_directories(fs::path(full_path).parent_path());

        std::ofstream out(full_path);
        if (!out.is_open()) {
            emit("scaffold", "FAILED to write file: " + rel_path, "error");
            return false;
        }
        out << content;
        out.close();
        emit("scaffold", "Generated -> " + rel_path);
    }
    emit("scaffold", "Scaffold complete.", "success");
    return true;
}

// ─────────────────────────────────────────────
//  Build runners
// ─────────────────────────────────────────────
bool run_cmd(const std::string& cmd, const std::string& stage) {
    emit(stage, "$ " + cmd);
    int ret = std::system(cmd.c_str());
    if (ret != 0) {
        emit(stage, "Command exited with code " + std::to_string(ret), "error");
        return false;
    }
    return true;
}

bool build_web(const std::string& ws) {
    emit("build", "Detected project type: Web App");
    if (!run_cmd("cd " + ws + " && npm install --silent", "build")) return false;
    if (!run_cmd("cd " + ws + " && npm run build",        "build")) return false;
    emit("build", "Web build finished.", "success");
    return true;
}

bool build_android(const std::string& ws) {
    emit("build", "Detected project type: Android APK");
    // Check Gradle wrapper presence
    if (!fs::exists(ws + "/gradlew")) {
        emit("build", "gradlew not found – injecting Gradle Wrapper stub.", "warn");
        run_cmd("cd " + ws + " && gradle wrapper", "build");
    }
    if (!run_cmd("cd " + ws + " && chmod +x gradlew && ./gradlew assembleDebug", "build")) return false;
    emit("build", "Android build finished.", "success");
    return true;
}

// ─────────────────────────────────────────────
//  Packager
// ─────────────────────────────────────────────
bool package_output(const std::string& ws, const std::string& project_name, const std::string& type) {
    emit("package", "Archiving build artifacts...");
    std::string out_zip = "../output_" + project_name + ".zip";
    std::string src = (type == "android")
        ? ws + "/app/build/outputs/apk/debug/"
        : ws + "/dist/";

    if (!fs::exists(src)) {
        emit("package", "Output directory not found: " + src, "error");
        return false;
    }

    std::string cmd = "zip -r " + out_zip + " " + src;
    if (!run_cmd(cmd, "package")) return false;

    emit("package", "Artifact ready: " + out_zip, "success");
    return true;
}

// ─────────────────────────────────────────────
//  Entry point
// ─────────────────────────────────────────────
int main(int argc, char* argv[]) {
    emit("init", "========== ANTIGRAVITY C++ BUILDER ENGINE ==========");

    if (argc < 2) {
        emit("init", "Usage: builder <path_to_payload.json>", "error");
        return 1;
    }

    std::ifstream file(argv[1]);
    if (!file.is_open()) {
        emit("init", std::string("Cannot open payload: ") + argv[1], "error");
        return 1;
    }

    json payload;
    try {
        file >> payload;
    } catch (const json::exception& e) {
        emit("init", std::string("JSON parse error: ") + e.what(), "error");
        return 1;
    }

    std::string project_name = payload.value("project_name", "generated_app");
    std::string project_type = payload.value("type", "web");   // "web" | "android"

    emit("init", "Project: " + project_name + "  |  Type: " + project_type);

    std::string workspace = "./build_workspace/" + project_name;

    // 1. Scaffold
    if (payload.contains("files")) {
        if (!scaffold_files(payload["files"], workspace)) return 1;
    } else {
        emit("scaffold", "No files key in payload – skipping scaffold.", "warn");
    }

    // 2. Compile
    bool build_ok = false;
    if (project_type == "web")         build_ok = build_web(workspace);
    else if (project_type == "android") build_ok = build_android(workspace);
    else {
        emit("build", "Unknown project type '" + project_type + "' – skipping compile.", "warn");
        build_ok = true;
    }
    if (!build_ok) return 1;

    // 3. Package
    if (!package_output(workspace, project_name, project_type)) return 1;

    emit("done", "Build pipeline finished successfully!", "success");
    return 0;
}
