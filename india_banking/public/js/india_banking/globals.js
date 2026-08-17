import BankLogoCard from "./components/BankLogoCard.vue";
import AvailableBanks from "./components/AvailableBanks.vue";
import ConnectedBankList from "./components/ConnectedBankList.vue";
import ConnectedBankCard from "./components/ConnectedBankCard.vue";
import AddBankCard from "./components/AddBankCard.vue";
import DoctypeLinks from "./components/DoctypeLinks.vue";
import SkeletonCard from "./components/SkeletonCard.vue";
import Sidebar from "./components/Sidebar.vue";

export function registerGlobalComponents(app) {
	app.component("Sidebar", Sidebar);
	app.component("BankLogoCard", BankLogoCard);
	app.component("AvailableBanks", AvailableBanks);
	app.component("ConnectedBankList", ConnectedBankList);
	app.component("ConnectedBankCard", ConnectedBankCard);
	app.component("SkeletonCard", SkeletonCard);
	app.component("DoctypeLinks", DoctypeLinks);
	app.component("AddBankCard", AddBankCard);
}
