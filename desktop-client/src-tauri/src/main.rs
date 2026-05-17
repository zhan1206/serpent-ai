// SerpentAI Desktop Client - Tauri 2.x Entry Point
// Launches Tauri app with system tray and global shortcut

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    Manager,
};

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .setup(|app| {
            let show_i = MenuItem::with_id(app, "show", "Show Window", true, None::<&str>)?;
            let quit_i = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show_i, &quit_i])?;

            let _tray = TrayIconBuilder::new()
                .menu(&menu)
                .tooltip("SerpentAI")
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => {
                        if let Some(w) = app.get_webview_window("main") {
                            w.show().unwrap();
                            w.set_focus().unwrap();
                        }
                    }
                    "quit" => app.exit(0),
                    _ => {}
                })
                .build(app)?;

            // Global shortcut Ctrl+Shift+S for voice input
            app.global_shortcut().on_shortcuts(
                ["ctrl+shift+s"],
                |_app, _shortcut, _event| {
                    if let Some(w) = _app.get_webview_window("main") {
                        w.eval("window.__triggerVoiceInput && window.__triggerVoiceInput();").ok();
                    }
                },
            )?;

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("Failed to start");
}
