use std::process::{Child, Command};
use std::sync::Mutex;

use tauri::menu::{MenuBuilder, MenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::{Manager, RunEvent};

/// Holds the spawned FastAPI backend process so we can stop it on exit.
struct Backend(Mutex<Option<Child>>);

/// Python interpreter to launch the backend with.
///
/// Overridable via the `AICM_PYTHON` env var (e.g. a bundled venv). Defaults to
/// the platform's usual interpreter name.
fn python_command() -> String {
    if let Ok(p) = std::env::var("AICM_PYTHON") {
        return p;
    }
    if cfg!(windows) {
        "python".into()
    } else {
        "python3".into()
    }
}

/// Launch the backend (uvicorn) from the bundled `backend/` resources.
///
/// `backend/` and `registry/` are bundled as resources, so running with the
/// resource directory as the working directory lets `backend.main:app` import
/// and the registry path resolve correctly.
fn spawn_backend(app: &tauri::AppHandle) -> Option<Child> {
    let resource_dir = match app.path().resource_dir() {
        Ok(dir) => dir,
        Err(e) => {
            eprintln!("Could not resolve resource dir: {e}");
            return None;
        }
    };
    let py = python_command();
    println!(
        "Starting backend: {py} -m uvicorn (cwd={})",
        resource_dir.display()
    );
    match Command::new(&py)
        .args([
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--log-level",
            "info",
        ])
        .current_dir(&resource_dir)
        .spawn()
    {
        Ok(child) => Some(child),
        Err(e) => {
            eprintln!("Failed to launch backend with '{py}': {e}");
            eprintln!("Ensure Python 3.11+ and the backend deps are installed, or set AICM_PYTHON.");
            None
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(Backend(Mutex::new(None)))
        .setup(|app| {
            // 1. Start the local backend.
            let handle = app.handle().clone();
            if let Some(child) = spawn_backend(&handle) {
                *app.state::<Backend>().0.lock().unwrap() = Some(child);
            }

            // 2. System tray with Show / Quit.
            let show = MenuItem::with_id(app, "show", "Show Window", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = MenuBuilder::new(app).items(&[&show, &quit]).build()?;

            TrayIconBuilder::with_id("main")
                .icon(app.default_window_icon().unwrap().clone())
                .tooltip("AI Connector Marketplace")
                .menu(&menu)
                .on_menu_event(|app, event| match event.id().as_ref() {
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "quit" => app.exit(0),
                    _ => {}
                })
                .build(app)?;

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building AI Connector Marketplace")
        .run(|app_handle, event| {
            // Stop the backend when the app is exiting.
            if let RunEvent::ExitRequested { .. } = event {
                if let Some(state) = app_handle.try_state::<Backend>() {
                    if let Some(mut child) = state.0.lock().unwrap().take() {
                        let _ = child.kill();
                    }
                }
            }
        });
}
