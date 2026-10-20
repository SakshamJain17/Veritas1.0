import "./styles.css";
import "../../../packages/shared/brand.css";
import {ThemeProvider} from '../../../packages/shared/theme';
import {THEME_INIT_SCRIPT} from '../../../packages/shared/theme-init';
import './themes.css';
export const metadata={title:"Veritas Demo Registry",icons:{icon:[{url:"/brand/veritas-mark-light.svg",media:"(prefers-color-scheme: light)"},{url:"/brand/veritas-mark-dark.svg",media:"(prefers-color-scheme: dark)"}]}};
export default function L({children}:{children:React.ReactNode}){return <html lang="en" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{__html:THEME_INIT_SCRIPT}}/></head><body><ThemeProvider>{children}</ThemeProvider></body></html>}
