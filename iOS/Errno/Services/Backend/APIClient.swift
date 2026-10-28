import Foundation

/// Configuration contains a public API origin only. Database credentials never belong here.
nonisolated struct BackendConfiguration: Sendable {
    let baseURL: URL

    init(baseURL: URL) throws {
        guard var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false),
              let host = components.host, components.user == nil, components.password == nil,
              components.query == nil, components.fragment == nil else { throw APIError.configuration }
        var allowed = components.scheme == "https"
        #if DEBUG
        allowed = allowed || (components.scheme == "http" && ["localhost", "127.0.0.1", "::1"].contains(host))
        #endif
        guard allowed else { throw APIError.configuration }
        components.path = components.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        if !components.path.isEmpty { components.path = "/" + components.path }
        guard let url = components.url else { throw APIError.configuration }
        self.baseURL = url
    }

    static func bundled() throws -> Self {
        #if DEBUG
        if let value = ProcessInfo.processInfo.environment["ERRNO_API_BASE_URL"], let url = URL(string: value) {
            return try Self(baseURL: url)
        }
        #endif
        guard let value = Bundle.main.object(forInfoDictionaryKey: "ErrnoAPIBaseURL") as? String,
              let url = URL(string: value) else { throw APIError.configuration }
        return try Self(baseURL: url)
    }
}

nonisolated enum APIError: Error, LocalizedError, Equatable {
    case configuration, invalidResponse, decoding, unauthorized, forbidden, notFound
    case validation, rateLimited, server, transport, timedOut
    case insecureAuthentication, unsupportedFeature, invalidInput

    var errorDescription: String? {
        switch self {
        case .configuration: return "The backend address has not been configured correctly."
        case .invalidResponse, .decoding: return "The server returned an unsupported response."
        case .unauthorized: return "Your session has expired. Please sign in again."
        case .forbidden: return "You do not have permission to perform this action."
        case .notFound: return "This record is no longer available."
        case .validation, .invalidInput: return "Please check the information you entered."
        case .rateLimited: return "Too many requests. Please try again later."
        case .server: return "The server is unavailable. Please try again."
        case .transport: return "Unable to connect. Check your connection and retry."
        case .timedOut: return "The request timed out. Please retry."
        case .insecureAuthentication: return "Sign-in is unavailable until the backend supports secure OTP verification and sessions."
        case .unsupportedFeature: return "This feature is not supported by the current backend."
        }
    }
}

nonisolated struct APIEndpoint: Sendable {
    let method: String
    let path: [String]
    var query: [URLQueryItem] = []
    var body: Data? = nil

    // Snake case is explicit in DTOs; no global key conversion can silently rename IDs.
    static func json<T: Encodable>(_ method: String, _ path: [String], body: T) throws -> Self {
        Self(method: method, path: path, body: try JSONEncoder().encode(body))
    }
}

nonisolated protocol APITransport: Sendable {
    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse)
}

nonisolated private final class RejectRedirects: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}

nonisolated final class URLSessionTransport: APITransport, @unchecked Sendable {
    private let session: URLSession
    init() {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = 30
        configuration.timeoutIntervalForResource = 60
        configuration.httpCookieStorage = nil
        configuration.urlCredentialStorage = nil
        session = URLSession(configuration: configuration, delegate: RejectRedirects(), delegateQueue: nil)
    }
    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let (data, response) = try await session.data(for: request)
        guard let response = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        // Reject redirects instead of forwarding future session credentials to another origin.
        guard response.url == request.url else { throw APIError.invalidResponse }
        return (data, response)
    }
}

nonisolated struct APIClient: Sendable {
    let configuration: BackendConfiguration
    let transport: any APITransport
    init(configuration: BackendConfiguration, transport: any APITransport = URLSessionTransport()) {
        self.configuration = configuration
        self.transport = transport
    }

    func request(for endpoint: APIEndpoint) throws -> URLRequest {
        var url = configuration.baseURL
        for segment in endpoint.path {
            guard !segment.isEmpty, segment != ".", segment != "..", !segment.contains("/"),
                  !segment.contains("\\"), !segment.contains("%") else { throw APIError.invalidInput }
            url.appendPathComponent(segment)
        }
        guard var components = URLComponents(url: url, resolvingAgainstBaseURL: false) else { throw APIError.configuration }
        if !endpoint.query.isEmpty { components.queryItems = endpoint.query }
        guard let finalURL = components.url else { throw APIError.configuration }
        var request = URLRequest(url: finalURL, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 30)
        request.httpMethod = endpoint.method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body = endpoint.body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        return request
    }

    @concurrent
    func send<T: Decodable & Sendable>(_ endpoint: APIEndpoint, as type: T.Type = T.self) async throws -> T {
        try Task.checkCancellation()
        let request = try request(for: endpoint)
        let data: Data
        let response: HTTPURLResponse
        do { (data, response) = try await transport.data(for: request) }
        catch is CancellationError { throw CancellationError() }
        catch let error as APIError { throw error }
        catch let error as URLError {
            if error.code == .cancelled { throw CancellationError() }
            throw error.code == .timedOut ? APIError.timedOut : APIError.transport
        } catch { throw APIError.transport }
        try Task.checkCancellation()
        switch response.statusCode {
        case 200..<300: break
        case 401: throw APIError.unauthorized
        case 403: throw APIError.forbidden
        case 404: throw APIError.notFound
        case 400, 409, 422: throw APIError.validation
        case 429: throw APIError.rateLimited
        case 500...599: throw APIError.server
        default: throw APIError.invalidResponse
        }
        // Do not show raw server errors: validation bodies can echo OTPs and personal data.
        do { return try JSONDecoder().decode(T.self, from: data) }
        catch { throw APIError.decoding }
    }
}
