// A window on Safari's own engine (WebKit), for tools/try_safari.sh: it opens a page and runs scripts in it one
// after another.  A script run from here is, to the page, a person's click - which is what a browser asks for before it
// lets a page make sound - so each step that presses something is a script of its own.  A script that posts "next"
// hands on to the following one, and one that posts "snap:" and the name of a file has a picture of the page put
// there first; anything else it posts is printed, and the window closes.
//
//     window URL step1.js step2.js ... [show]

import Cocoa
import WebKit

final class Nav: NSObject, WKNavigationDelegate, WKScriptMessageHandler {
    var scripts: [String] = []
    var at = 0
    weak var web: WKWebView?
    func step() {                                  // each script is run from here: to the page that is a person's click
        guard at < scripts.count else { return }
        let s = scripts[at]; at += 1
        web?.evaluateJavaScript(s) { _, err in if let e = err as NSError?, e.code != 5 { print("ERR \(e)"); exit(2) } }
    }
    func webView(_ w: WKWebView, didFinish n: WKNavigation!) { if at == 0 { step() } }
    func userContentController(_ c: WKUserContentController, didReceive m: WKScriptMessage) {
        let body = m.body as? String ?? "?"
        if body == "next" { step() }
        else if body.hasPrefix("snap:"), let w = web {              // a picture of the page as it is, then on to the next script
            let path = String(body.dropFirst(5))
            w.takeSnapshot(with: nil) { image, _ in
                if let tiff = image?.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff), let png = rep.representation(using: .png, properties: [:]) {
                    try? png.write(to: URL(fileURLWithPath: path))
                }
                self.step()
            }
        }
        else { print(body); fflush(stdout); exit(0) }
    }
}
let args = CommandLine.arguments
let app = NSApplication.shared
app.setActivationPolicy(.accessory)
let cfg = WKWebViewConfiguration()
cfg.mediaTypesRequiringUserActionForPlayback = .all
let nav = Nav()
nav.scripts = args.dropFirst(2).filter { $0 != "show" && $0 != "see" }.map { try! String(contentsOfFile: $0, encoding: .utf8) }
cfg.userContentController.add(nav, name: "out")
let web = WKWebView(frame: NSRect(x: 0, y: 0, width: 860, height: 700), configuration: cfg)
web.navigationDelegate = nav
nav.web = web
let win = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 860, height: 700), styleMask: [.titled], backing: .buffered, defer: false)
win.contentView = web
// A window behind others is treated as hidden: the page in it is given no frames and its clocks are slowed until a test
// of a minute takes many.  So this one floats above the rest where nothing can cover it - and, unless "see" is asked
// for, so faint that it is not in anyone's way.  It takes no clicks and no keys from whoever is at the computer.
if args.contains("show") || args.contains("see") {
    win.level = .floating
    win.ignoresMouseEvents = true
    if !args.contains("see") { win.alphaValue = 0.02 }
    if let screen = NSScreen.main { win.setFrameTopLeftPoint(NSPoint(x: screen.visibleFrame.minX + 20, y: screen.visibleFrame.maxY - 20)) }
    win.orderFrontRegardless()
}
let awake = ProcessInfo.processInfo.beginActivity(options: [.userInitiated, .latencyCritical], reason: "trying the page")
_ = awake
if args[1].hasPrefix("http") { web.load(URLRequest(url: URL(string: args[1])!)) } else { web.loadHTMLString(try! String(contentsOfFile: args[1], encoding: .utf8), baseURL: URL(string: "http://127.0.0.1/")) }
DispatchQueue.main.asyncAfter(deadline: .now() + 150) { print("TIMEOUT"); exit(1) }
app.run()
