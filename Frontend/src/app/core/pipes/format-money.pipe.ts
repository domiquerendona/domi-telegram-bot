import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'fmtMoney', standalone: true })
export class FormatMoneyPipe implements PipeTransform {
  transform(value: number | null | undefined): string {
    if (!value) return '$0';
    return '$' + value.toLocaleString('es-CO');
  }
}
