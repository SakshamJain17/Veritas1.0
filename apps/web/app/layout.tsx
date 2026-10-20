import "./styles.css";
import {GeistSans} from 'geist/font/sans';
import {GeistMono} from 'geist/font/mono';
import {ThemeProvider} from '../../../packages/shared/theme';
import {THEME_INIT_SCRIPT} from '../../../packages/shared/theme-init';
import './themes.css';
export const metadata = { title: "VERITAS · Proof of Reality", description: "Evidence-first document verification",icons:{icon:[{url:"/brand/veritas-mark-light.svg",media:"(prefers-color-scheme: light)"},{url:"/brand/veritas-mark-dark.svg",media:"(prefers-color-scheme: dark)"}]}};
export default function Layout({children}:{children:React.ReactNode}) { return <html lang="en" suppressHydrationWarning className={`${GeistSans.variable} ${GeistMono.variable}`}><head><script dangerouslySetInnerHTML={{__html:THEME_INIT_SCRIPT}}/></head><body><ThemeProvider>{children}</ThemeProvider></body></html> }
