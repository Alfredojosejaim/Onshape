// Predicados de tipo centralizados (frontera de parseo).
//
// Todo `typeof` de estrechamiento vive aquí, dentro de predicados, bajo la
// opción `allowInTypeGuards` de anti-slop/no-runtime-typeof. El resto del
// código estrecha llamando a estos predicados en vez de usar `typeof` ad hoc.
// El sujeto `unknown` está permitido por la regla al ser el sujeto exacto de
// un predicado de tipo.
import type { JsonValue } from '../types';

/** Objeto plano JSON (no array, no null). */
export function isRecord(v: unknown): v is Record<string, JsonValue> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

/** Número (incluye NaN/Inf; usar isFiniteNumber si se necesita finito). */
export function isNumber(v: unknown): v is number {
  return typeof v === 'number';
}

/** Número finito. */
export function isFiniteNumber(v: unknown): v is number {
  return typeof v === 'number' && Number.isFinite(v);
}

/** Cadena. */
export function isString(v: unknown): v is string {
  return typeof v === 'string';
}

/** Booleano. */
export function isBoolean(v: unknown): v is boolean {
  return typeof v === 'boolean';
}

/** Función del bridge pywebview: (...args: string[]) => Promise<JsonValue>. */
export function isBridgeFunction(
  v: unknown,
): v is (...a: string[]) => Promise<JsonValue> {
  return typeof v === 'function';
}

/** Valor serializable a JSON (lo que pywebview entrega tras JSON.parse). */
export function isJsonValue(v: unknown): v is JsonValue {
  if (v === null) return true;

  if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') return true;

  if (Array.isArray(v)) return v.every(isJsonValue);

  if (isRecord(v)) return Object.values(v).every(isJsonValue);

  return false;
}
