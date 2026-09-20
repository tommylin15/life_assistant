sealed class AppError {
  final String message;
  final Object? cause;
  const AppError(this.message, {this.cause});
}

// 網路 / Google 服務暫時失敗，可重試
class NetworkError extends AppError {
  const NetworkError(super.message, {super.cause});
}

// Google token 過期或未授權
class AuthError extends AppError {
  const AuthError(super.message, {super.cause});
}

// 使用者需要採取行動（衝突、權限等）
class UserActionRequired extends AppError {
  final String actionLabel;
  const UserActionRequired(
    super.message, {
    required this.actionLabel,
    super.cause,
  });
}

// SQLite migration 失敗 / DB 損毀
class DataIntegrityError extends AppError {
  const DataIntegrityError(super.message, {super.cause});
}

// Bridge schema 不相容
class BridgeSchemaError extends AppError {
  const BridgeSchemaError(super.message, {super.cause});
}

// 一般驗證錯誤
class ValidationError extends AppError {
  const ValidationError(super.message, {super.cause});
}

// 未預期錯誤
class UnknownError extends AppError {
  const UnknownError(super.message, {super.cause});
}
