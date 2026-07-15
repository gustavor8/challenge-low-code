export const errorMessages: Record<string, (err?: any) => string> = {
  required: () => 'Este campo é obrigatório.',
  email: () => 'E-mail inválido.',
  min: (err) => `O valor mínimo é ${err.min}.`,
  max: (err) => `O valor máximo é ${err.max}.`,
  gt: (err) => `O valor deve ser maior que ${err.requiredGt || 0}.`,
  pattern: () => 'Formato inválido.'
};

export function getErrorMessage(controlName: string, errors: Record<string, any> | null): string {
  if (!errors) return '';
  const firstErrorKey = Object.keys(errors)[0];
  const errorFn = errorMessages[firstErrorKey];
  return errorFn ? errorFn(errors[firstErrorKey]) : 'Campo inválido.';
}
