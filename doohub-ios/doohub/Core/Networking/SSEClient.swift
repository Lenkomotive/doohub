import Foundation

struct SSEEvent {
    let event: String?
    let data: String
}

class SSEClient {
    private var task: URLSessionDataTask?
    private let url: URL
    private var onEvent: ((SSEEvent) -> Void)?
    private var onError: ((Error?) -> Void)?
    private var retryCount = 0
    private let maxRetries = 10

    init(url: URL) {
        self.url = url
    }

    func connect(onEvent: @escaping (SSEEvent) -> Void, onError: ((Error?) -> Void)? = nil) {
        self.onEvent = onEvent
        self.onError = onError
        startConnection()
    }

    private func startConnection() {
        var request = URLRequest(url: url)
        request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
        request.timeoutInterval = TimeInterval(Int.max)

        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = TimeInterval(Int.max)
        config.timeoutIntervalForResource = TimeInterval(Int.max)

        let session = URLSession(configuration: config, delegate: SSEDelegate(client: self), delegateQueue: nil)
        task = session.dataTask(with: request)
        task?.resume()
    }

    func disconnect() {
        task?.cancel()
        task = nil
        retryCount = 0
    }

    fileprivate var buffer = ""

    fileprivate func processBuffer() {
        let lines = buffer.components(separatedBy: "\n")
        var currentEvent: String? = nil
        var currentData = ""

        var i = 0
        while i < lines.count {
            let line = lines[i]

            if line.isEmpty {
                // Empty line = end of event
                if !currentData.isEmpty {
                    let event = SSEEvent(event: currentEvent, data: currentData.trimmingCharacters(in: .whitespacesAndNewlines))
                    DispatchQueue.main.async { [weak self] in
                        self?.onEvent?(event)
                    }
                }
                currentEvent = nil
                currentData = ""
                // Clear processed lines from buffer
                buffer = lines[(i+1)...].joined(separator: "\n")
                i += 1
                continue
            }

            if line.hasPrefix("event:") {
                currentEvent = String(line.dropFirst(6)).trimmingCharacters(in: .whitespaces)
            } else if line.hasPrefix("data:") {
                let data = String(line.dropFirst(5)).trimmingCharacters(in: .whitespaces)
                if !currentData.isEmpty {
                    currentData += "\n"
                }
                currentData += data
            }

            i += 1
        }
    }

    fileprivate func handleError(_ error: Error?) {
        guard retryCount < maxRetries else {
            DispatchQueue.main.async { [weak self] in
                self?.onError?(error)
            }
            return
        }

        retryCount += 1
        let delay = min(pow(2.0, Double(retryCount)), 30.0)
        DispatchQueue.global().asyncAfter(deadline: .now() + delay) { [weak self] in
            self?.startConnection()
        }
    }
}

private class SSEDelegate: NSObject, URLSessionDataDelegate {
    weak var client: SSEClient?

    init(client: SSEClient) {
        self.client = client
    }

    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive data: Data) {
        guard let string = String(data: data, encoding: .utf8) else { return }
        client?.buffer += string
        client?.processBuffer()
    }

    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        if let urlError = error as? URLError, urlError.code == .cancelled {
            return
        }
        client?.handleError(error)
    }
}
