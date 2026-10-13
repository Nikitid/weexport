import Foundation
import CryptoKit

let arguments = CommandLine.arguments
let key = try Curve25519.Signing.PublicKey(rawRepresentation: Data(base64Encoded: arguments[1])!)
let signature = Data(base64Encoded: arguments[2])!
let data = try Data(contentsOf: URL(fileURLWithPath: arguments[3]))
let count = arguments.count > 4 ? Int(arguments[4])! : data.count
guard count >= 0, count <= data.count,
      key.isValidSignature(signature, for: data.prefix(count)) else {
    fputs("Invalid update signature\n", stderr)
    exit(1)
}
